# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path
from typing import Dict, List, Mapping, Optional

import libcst as cst
from libcst._position import CodeRange
from libcst.helpers import calculate_module_and_package
from libcst.metadata.base_provider import BatchableMetadataProvider
from libcst.metadata.position_provider import PositionProvider

import mypy
import mypy.build
import mypy.main
import mypy.nodes


from libcst_mypy.utils import (
    MypyType,
    MypyTypeInferenceProviderCache,
    CodeRangeToMypyNodesBinder,
)


class MypyTypeInferenceProvider(
    BatchableMetadataProvider[MypyType]  # type: ignore[misc]
):
    """
    Access inferred type annotation through `mypy <http://mypy-lang.org/>`_.
    """

    METADATA_DEPENDENCIES = (PositionProvider,)

    @classmethod
    def gen_cache(
        cls, root_path: Path, paths: List[str], timeout: Optional[int] = None
    ) -> Mapping[str, Optional[MypyTypeInferenceProviderCache]]:
        targets, options = mypy.main.process_options(paths)
        options.preserve_asts = True
        options.fine_grained_incremental = True
        options.use_fine_grained_cache = True
        mypy_result = mypy.build.build(targets, options=options)
        cache = {}
        for path in paths:
            module = calculate_module_and_package(str(root_path), path).name
            mypy_file = mypy_result.graph[module].tree
            if mypy_file is not None:
                cache[path] = MypyTypeInferenceProviderCache(
                    module_name=module, mypy_file=mypy_file
                )
        return cache

    def __init__(self, cache: Optional[MypyTypeInferenceProviderCache]) -> None:
        super().__init__(cache)
        self._mypy_node_locations: Dict[CodeRange, "mypy.nodes.Node"] = {}
        if cache is None:
            return
        code_range_to_mypy_nodes_binder = CodeRangeToMypyNodesBinder(cache.module_name)
        code_range_to_mypy_nodes_binder.visit_mypy_file(cache.mypy_file)
        self._mypy_node_locations = (
            code_range_to_mypy_nodes_binder.locations  # type: ignore[assignment]
        )

    def _parse_metadata(self, node: cst.CSTNode) -> None:
        range = self.get_metadata(PositionProvider, node)
        if range in self._mypy_node_locations:
            self.set_metadata(node, self._mypy_node_locations.get(range))

    def visit_Name(self, node: cst.Name) -> None:
        self._parse_metadata(node)

    def visit_Attribute(self, node: cst.Attribute) -> None:
        self._parse_metadata(node)

    def visit_Call(self, node: cst.Call) -> None:
        self._parse_metadata(node)
