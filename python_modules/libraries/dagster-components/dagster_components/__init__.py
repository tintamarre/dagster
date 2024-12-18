from dagster_components.core.component import (
    Component as Component,
    ComponentLoadContext as ComponentLoadContext,
    ComponentRegistry as ComponentRegistry,
    component as component,
)
from dagster_components.core.component_defs_builder import (
    build_defs_from_toplevel_components_folder as build_defs_from_toplevel_components_folder,
)
from dagster_components.impls.dbt_project import DbtProjectComponent
from dagster_components.impls.pipes_subprocess_script_collection import (
    PipesSubprocessScriptCollection,
)
from dagster_components.impls.sling_replication import SlingReplicationComponent

__component_registry__ = {
    "pipes_subprocess_script_collection": PipesSubprocessScriptCollection,
    "sling_replication": SlingReplicationComponent,
    "dbt_project": DbtProjectComponent,
}

from dagster._core.libraries import DagsterLibraryRegistry

from dagster_components.version import __version__ as __version__

DagsterLibraryRegistry.register("dagster-components", __version__)
