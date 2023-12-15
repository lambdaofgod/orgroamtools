import os
import re
import warnings
import sqlite3 as sql
import copy
from typing import Iterable
from dataclasses import dataclass

import networkx as nx

from orgroamtools._RoamGraphHelpers import IdentifierType, DuplicateTitlesWarning


@dataclass
class RoamNode:
    fname: str
    title: str
    id: str
    tags: set[str]
    links: list[str]


class RoamGraph:
    """Object to store data associated to a collection of org-roam nodes"""

    def __init__(self, db: str):
        """Initializes RoamGraph object

        The RoamGraph object stores information about the nodes in the
        collection described by the database path provided. The nodes also store
        information about how they relate to each other via backlinks.

        Parameters
        ----------
        db : str
            Path to org-roam database

        Examples
        --------
        FIXME: Add docs
        """

        super(RoamGraph, self).__init__()

        self.db_path = os.path.expanduser(db)
        if not os.path.isfile(self.db_path):
            raise AttributeError(f"No such file or directory: {self.db_path}")

        self._fnames = self.__init_fnames(self.db_path)
        self._titles = self.__init_titles(self.db_path)

        seen = set()
        self._duplicate_titles = [x for x in self._titles if x in seen or seen.add(x)]
        self._contains_dup_titles = len(self._duplicate_titles) > 0
        if self._contains_dup_titles:
            warnings.warn(
                "Collection contains duplicate titles. Matching nodes by title will be non-exhaustive.",
                DuplicateTitlesWarning,
            )

        self._ids = self.__init_ids(self.db_path)
        self._tags = self.__init_tags(self.db_path)
        self._links_to = self.__init_links_to(self.db_path)

        self._id_title_map = {
            self._ids[i]: self._titles[i] for i in range(len(self._ids))
        }

        self._graph = nx.MultiDiGraph(
            {self._ids[i]: self._links_to[i] for i in range(len(self._titles))}
        )
        self._node_index = {
            j[2]: RoamNode(j[0], j[1], j[2], j[3], j[4])
            for j in zip(
                self._fnames, self._titles, self._ids, self._tags, self._links_to
            )
        }

        self._orphans = [
            node
            for node in self._node_index.values()
            if not any(
                [self._nodes_linked(node, other) for other in self._node_index.values()]
            )
        ]

        self._is_connected = self._orphans == []

    @property
    def graph(self) -> nx.MultiDiGraph:
        """Return networkx graph representation of collection

        The collection of org-roam nodes and their backlinks naturally form a
        directed multigraph. That is, a graph with nodes and directed arrows,
        where we allow mutiple arrows between any pair of nodes. The number of
        arrows between two nodes NODE1 and NODE2 is the number of times the
        backlink for NODE2 appears in the text of NODE1. Networkx has a special
        type of graph object networkx.MultiDiGraph to represent such a graph,
        which is returned here for the instantiated collection of org-roam nodes

        Returns
        -------
        nx.MultiDiGraph
            Multi directed graph representation of the collection

        Examples
        --------
        FIXME: Add docs.
        """

        return self._graph

    @graph.setter
    def graph(self, value: nx.MultiDiGraph) -> None:
        """Setter for graph attribute

        Parameters
        ----------
        value : nx.MultiDiGraph
            new graph to set self._graph to

        Examples
        --------
        FIXME: Add docs.

        """

        self._graph = value

    @property
    def backlink_index(self) -> dict[str, list[str]]:
        """Return index for node backlinks of the collection

        When a node in the collection has a reference to another node in the
        collection, it is said to have a backlink to that node.

        Returns
        -------
        dict[str, list[str]]
            dict of (k,v) pairs where k is a node ID and v is a list of
            backlinks of the node with ID k

        Examples
        --------
        FIXME: Add docs.
        """

        return {node.id: node.links for node in self._node_index.values()}

    @property
    def file_index(self) -> dict[str, str]:
        """Return index of filenames of collection

        Since multiple nodes can exist in a single file, it may be helpful to
        retrieve the name of the file where a particular node is located.

        Returns
        -------
        dict[str, list[str]]
            dict of (k,v) pairs where k is a node ID and v is a string for the
            path of the location of the node with ID k

        Examples
        --------
        FIXME: Add docs.

        """
        return {node.id: node.fname for node in self._node_index}

    @property
    def node_info(self) -> list[RoamNode]:
        """Return index of nodes

        Grabs list of RoamNode objects from collection

        Returns
        -------
        list[Node]
            List of RoamNode objects in collection
        """
        return self._node_index

    @node_info.setter
    def node_index(self, value: dict[str, RoamNode]) -> None:
        """Setter for node index

        Parameters
        ----------
        value : dict[str,RoamNode]
            New node index
        """
        self._node_index = value

    def __filter_tags(self, tags: list[str], exclude: bool) -> None:
        """Filter network by tags



        Parameters
        ----------
        tags : list[str]
            List of tags to filter by
        exclude : bool
            Whether to exclude the tags in the new network or not
        """
        tfilter = [node.has_tag(tags) for node in self.nodes]
        if exclude:
            tfilter = [not b for b in tfilter]
        self.nodes = [node for (node, b) in zip(self.nodes, tfilter) if b]

    def __init_ids(self, dbpath: str) -> list[str]:
        """Initializes list of IDs for each node
        Params
        dbpath -- str
              database path

        Returns list of roam-node ids
        """
        id_query = "SELECT id FROM nodes ORDER BY id ASC;"
        try:
            with sql.connect(dbpath, uri=True) as con:
                csr = con.cursor()
                query = csr.execute(id_query)
                return [i[0].replace('"', "") for i in query.fetchall()]

        except sql.Error as e:
            print("Connection failed: ", e)

    def __init_fnames(self, dbpath: str) -> list[str]:
        """
        Initializes list of filenames for each node

        Params
        dbpath -- str
               database path


        Returns list of roam-node filepaths
        """
        fname_query = "SELECT file FROM nodes ORDER BY id ASC;"
        try:
            with sql.connect(dbpath, uri=True) as con:
                csr = con.cursor()
                query = csr.execute(fname_query)
                return [i[0].replace('"', "") for i in query.fetchall()]

        except sql.Error as e:
            print("Connection failed: ", e)

    def __init_titles(self, dbpath: str) -> list[str]:
        """
        Initializes list of titles for each node

        Params
        dbpath -- str
               database path


        Returns list of roam-node titles
        """
        title_query = "SELECT title FROM nodes ORDER BY id ASC;"
        try:
            with sql.connect(dbpath, uri=True) as con:
                csr = con.cursor()
                query = csr.execute(title_query)
                return [i[0].replace('"', "") for i in query.fetchall()]

        except sql.Error as e:
            print("Connection failed: ", e)

    def __init_tags(self, dbpath: str) -> list[set[str]]:
        """
        Initializes list of tags for each node

        Params
        dbpath -- str
                database path

        Returns list of roam-node taglists (as a set)
        """
        tags_query = "SELECT nodes.id, GROUP_CONCAT(tags.tag) AS tags FROM nodes LEFT JOIN tags ON nodes.id = tags.node_id GROUP BY nodes.id ORDER BY nodes.id ASC;"
        try:
            with sql.connect(dbpath, uri=True) as con:
                csr = con.cursor()
                query = csr.execute(tags_query)
                clean = lambda s: s.replace('"', "")
                match_null = lambda s: set() if not s else s.split(",")
                return [set(map(clean, match_null(i[1]))) for i in query.fetchall()]

        except sql.Error as e:
            print("Connection failed: ", e)

    def __init_links_to(self, dbpath: str) -> list[list[str]]:
        """
        Initializes list of links

        Params
        dbpath -- str
               database path


        Returns list of sets of roam-node links for each node
        """
        links_to_query = "SELECT n.id, GROUP_CONCAT(l.dest) FROM nodes n LEFT JOIN links l ON n.id = l.source GROUP BY n.id ORDER BY n.id ;"
        try:
            with sql.connect(dbpath, uri=True) as con:
                csr = con.cursor()
                query = csr.execute(links_to_query)
                clean = lambda s: s.replace('"', "")
                links = query.fetchall()

                return [
                    ([clean(i[0])] + list(map(clean, i[1].split(","))))
                    if i[1]
                    else [clean(i[0])]
                    for i in links
                ]

        except sql.Error as e:
            print("Connection failed: ", e)

    def remove_orphans(self):
        """
        Removes orphan nodes

        Returns orphanless RoamGraph (not done in-place)
        """
        orphanless = copy.copy(self)
        not_orphan = lambda node: not self.__is_orphan(node)

        orphanless.nodes = list(filter(not_orphan, self.nodes))

        return orphanless

    @property
    def fnames(self, base: bool = True) -> list[str]:
        """
        Get list of filenames of graph

        base -- bool (True)
              basenames of files

        Returns list of filenames
        """
        if base:
            return [os.path.basename(node.fname) for node in self.node_info.values()]

        return [node._fname for node in self.nodes]

    @property
    def nodes(self) -> list[RoamNode]:
        """
        Returns list of nodes
        """
        return list(self.node_info.values())

    @property
    def IDs(self) -> list[str]:
        """
        Returns list of node IDs
        """
        return [node.id for node in self.node_info.values()]

    @property
    def titles(self):
        """
        Returns list of node names (#+title file property)
        """
        return self._titles

    @property
    def links(self):
        """
        Returns tuples of (title, links) for each node
        """
        links = [a.links for a in self.nodes]
        return [(a, b) for (a, b) in zip(self.titles, links)]

    def __is_orphan(self, node: RoamNode) -> bool:
        """
        Checks if node is an orphan with respect to others

        Params:
        node -- node to check orphanhood

        Returns True if node is orphan of self
        """
        pointed_to = True if any(node.id in n.links for n in self.nodes) else False
        points_to = node.links != []
        return not points_to and not pointed_to

    def _identifier_type(self, identifier: str) -> IdentifierType:
        """
        Determines type of identifier
        """
        if identifier in self.IDs:
            return IdentifierType.ID
        elif identifier in self.titles:
            return IdentifierType.TITLE
        else:
            return IdentifierType.NOTHING

    def node_links(self, identifier: str) -> list[str]:
        """Return links for a particular node

        A node's links is the collection of links made in the body of the node desired.
        By convention, a node will always refer to itself

        Parameters
        ----------
        identifier : str
            Identifier for node. Can be title or ID

        Returns
        -------
        list[str]
            List of IDs of nodes the provided node refers to

        Raises
        ------
        AttributeError
            Raised if identifier cannot be found in the collection
        """

        identifier_type = self._identifier_type(identifier)

        match identifier_type:
            case IdentifierType.ID:
                return self._node_index[identifier].links

            case IdentifierType.TITLE:
                if identifier in self._duplicate_titles:
                    warnings.warn(
                        "Title is a duplicate. This might not be the desired result.",
                        DuplicateTitlesWarning,
                    )
                idx = self.IDs.index(identifier)
                return self.nodes[idx].links

            case IdentifierType.NOTHING:
                raise AttributeError(f"No node with identifier: {identifier}")

    def node(self, identifier: str) -> RoamNode:
        """Return node object

        Internally a node is of class orgroamtools.data.RoamNode, which stores
        basic information about a node like ID, title, filename, and its backlinks

        Parameters
        ----------
        identifier : str
            Identifier for node. Can be title or ID

        Returns
        -------
        RoamNode
            RoamNode object of node

        Raises
        ------
        AttributeError
            Raised if node cannot be found
        """
        identifier_type = self._identifier_type(identifier)

        match identifier_type:
            case IdentifierType.TITLE:
                if identifier in self._duplicate_titles:
                    warnings.warn(
                        "This title is duplicated. This may not be the node you want",
                        DuplicateTitlesWarning,
                    )
                idx = self.titles.index(identifier)
                return self.nodes[idx]

            case IdentifierType.ID:
                idx = self.Ids.index(identifier)
                return self.nodes[idx]

            case IdentifierType.NOTHING:
                raise AttributeError(f"No node with provided identifier: {identifier}")

        raise AttributeError("Uh oh spaghetti-o")

    def node_title(self, identifier: str) -> str:
        """Return title of node

        The title of a node is the name given to the note file.
        If your org-roam node is its own file, this is the #+title: property.
        If you org-roam node is a heading, this is the heading title

        Parameters
        ----------
        identifier : str
            ID of node

        Returns
        -------
        str
            Title of node

        Raises
        ------
        AttributeError
            Raised if ID not be found in collection
        """
        identifier_type = self._identifier_type(identifier)

        match identifier_type:
            case IdentifierType.ID:
                return self._id_title_map[identifier]

        raise AttributeError(f"No node with provided ID: {identifier}")

    def node_id(self, identifier: str) -> str:
        """Return ID of node

        org-roam uses org-mode's internal :ID: property creation to uniquely identify nodes
        in the collection.

        Parameters
        ----------
        identifier : str
            Title of node

        Returns
        -------
        str
            ID of node

        Raises
        ------
        AttributeError
            Raised if no node matches the provided title
        """

        identifier_type = self._identifier_type(identifier)
        print(identifier_type)

        match identifier_type:
            case IdentifierType.TITLE:
                if identifier_type in self._duplicate_titles:
                    warnings.warn(
                        "This title is duplicated. This may not be the ID you want.",
                        DuplicateTitlesWarning,
                    )
                index_of_id = self._titles.index(identifier)
                return self.IDs[index_of_id]

        raise AttributeError(f"No node with provided title: {identifier}")

    def filter_tags(self, tags, exclude=True):
        subgraph = copy.deepcopy(self)

        new_nodes = subgraph.__filtered_nodes(tags, exclude)

        subgraph._ids = [node.id for node in new_nodes]
        subgraph._titles = [node.title for node in new_nodes]
        subgraph._fnames = [node.fname for node in new_nodes]
        subgraph._links_to = [node.links for node in new_nodes]
        subgraph._graph = nx.MultiDiGraph(
            {
                subgraph._ids[i]: subgraph._links_to[i]
                for i in range(len(subgraph._titles))
            }
        )

        seen = set()
        subgraph._duplicate_titles = [
            x for x in subgraph._titles if x in seen or seen.add(x)
        ]
        subgraph._contains_dup_titles = len(subgraph._duplicate_titles) > 0
        if subgraph._contains_dup_titles:
            warnings.warn(
                "Collection contains duplicate titles. Matching nodes by title will be non-exhaustive.",
                DuplicateTitlesWarning,
            )

        subgraph._id_title_map = {
            subgraph._ids[i]: subgraph._titles[i] for i in range(len(subgraph._ids))
        }

        subgraph._node_index = {
            j[2]: RoamNode(j[0], j[1], j[2], j[3], j[4])
            for j in zip(
                subgraph._fnames,
                subgraph._titles,
                subgraph._ids,
                subgraph._tags,
                subgraph._links_to,
            )
        }

        # TODO This doesn't work. It need to remove the nodes not allowed in the subgraph in the
        # node.links_to for each node to properly detect if a node is an orphan
        subgraph._orphans = [
            node
            for node in subgraph._node_index.values()
            if not any(
                [
                    self._nodes_linked(node, other)
                    for other in subgraph._node_index.values()
                ]
            )
        ]

        subgraph._is_connected = subgraph._orphans == []
        return subgraph

    def _nodes_linked(node1: RoamNode, node2: RoamNode, directed: bool = True):
        if directed:
            return node2.id in node1.links
        else:
            return node2.id in node1.links or node1.id in node2.links

    def __filtered_nodes(self, tags: Iterable[str], exclude: bool) -> list[RoamNode]:
        """Filter network by exact matches on tags

        Parameters
        ----------
        tags : Iterable[str]
            Iterable of tags
        exclude : bool
            Whether to exclude in new network or not

        Returns
        -------
        list[RoamNode]
            List of filtered nodes

        Examples
        --------
        FIXME: Add docs.

        """

        tfilter = [
            any([tag in node.tags for tag in tags])
            for node in self._node_index.values()
        ]
        if exclude:
            tfilter = [not b for b in tfilter]
        return [node for (node, b) in zip(self.nodes, tfilter) if b]

    def _node_has_tag(self, node: RoamNode, tag: str) -> bool:
        return tag in node.tags

    def __filter_rx_tags(self, tags: Iterable[str], exclude: bool) -> list[RoamNode]:
        """Filter network by regex searches on tags

        Parameters
        ----------
        tags : Iterable[str]
            Iterable of regex strings
        exclude : bool
            To exclude the matched tags or not

        Examples
        --------
        FIXME: Add docs.
        """
        tags = set(map(re.compile, tags))

        # tfilter = [node.has_regex_tag(tags) for node in self.nodes]
        # Maybe????
        tfilter = [
            any([rx.match(tag) for tag in node.tags])
            for node in self._node_index.values()
            for rx in tags
        ]
        if exclude:
            tfilter = [not b for b in tfilter]
        return [node for (node, b) in zip(self.nodes, tfilter) if b]
