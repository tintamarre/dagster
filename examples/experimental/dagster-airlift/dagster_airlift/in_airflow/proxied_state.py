from pathlib import Path
from typing import Any, Dict, NamedTuple, Optional, Sequence

import yaml


class TaskProxiedState(NamedTuple):
    task_id: str
    proxied: bool

    @staticmethod
    def from_dict(task_dict: Dict[str, Any]) -> "TaskProxiedState":
        if set(task_dict.keys()) != {"id", "proxied"}:
            raise Exception(
                f"Expected 'proxied' and 'id' keys in the task dictionary. Found keys: {task_dict.keys()}"
            )
        if task_dict["proxied"] not in [True, False]:
            raise Exception("Expected 'proxied' key to be a boolean")
        return TaskProxiedState(task_id=task_dict["id"], proxied=task_dict["proxied"])

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.task_id, "proxied": self.proxied}


class DagProxiedState(NamedTuple):
    proxied: Optional[bool]
    tasks: Dict[str, TaskProxiedState]

    @staticmethod
    def from_dict(dag_dict: Dict[str, Any]) -> "DagProxiedState":
        if "tasks" not in dag_dict and "proxied" not in dag_dict:
            raise Exception(
                f"Expected a 'tasks' or 'proxied' top-level key in the dag dictionary. Instead; got: {dag_dict}"
            )
        if "tasks" in dag_dict and "proxied" in dag_dict:
            raise Exception(
                f"Expected only one of 'tasks' or 'proxied' top-level keys in the dag dictionary. Instead; got: {dag_dict}"
            )
        task_proxied_states = {}
        if "tasks" in dag_dict:
            task_list: Sequence[Dict[str, Any]] = dag_dict["tasks"]
            for task_dict in task_list:
                task_state = TaskProxiedState.from_dict(task_dict)
                task_proxied_states[task_state.task_id] = task_state
        dag_proxied_state: Optional[bool] = dag_dict.get("proxied")
        if dag_proxied_state not in [True, False, None]:
            raise Exception("Expected 'proxied' key to be a boolean or None")
        return DagProxiedState(tasks=task_proxied_states, proxied=dag_proxied_state)

    def to_dict(self) -> Dict[str, Sequence[Dict[str, Any]]]:
        return {"tasks": [task_state.to_dict() for task_state in self.tasks.values()]}

    def is_task_proxied(self, task_id: str) -> bool:
        if task_id not in self.tasks:
            return False
        return self.tasks[task_id].proxied

    @property
    def dag_proxies_at_task_level(self) -> bool:
        """Dags can proxy on either a task-by-task basis, or for the entire dag at once.
        We use the proxied state to determine which is the case for a given dag. If the dag's proxied state
        is None, then we assume the dag proxies at the task level. If the dag's proxied state is a boolean,
        then we assume the dag proxies at the dag level.
        """
        return self.proxied is None

    @property
    def dag_proxies_at_dag_level(self) -> bool:
        """Dags can proxy on either a task-by-task basis, or for the entire dag at once.
        We use the proxied state to determine which is the case for a given dag. If the dag's proxied state
        is None, then we assume the dag proxies at the task level. If the dag's proxied state is a boolean,
        then we assume the dag proxies at the dag level.
        """
        return self.proxied is not None


class AirflowProxiedState(NamedTuple):
    dags: Dict[str, DagProxiedState]

    def get_task_proxied_state(self, *, dag_id: str, task_id: str) -> Optional[bool]:
        if dag_id not in self.dags:
            return None
        if task_id not in self.dags[dag_id].tasks:
            return None
        return self.dags[dag_id].tasks[task_id].proxied

    def dag_has_proxied_state(self, dag_id: str) -> bool:
        return self.get_proxied_dict_for_dag(dag_id) is not None

    def dag_proxies_at_task_level(self, dag_id: str) -> bool:
        """Dags can proxy on either a task-by-task basis, or for the entire dag at once.
        We use the proxied state to determine which is the case for a given dag. If the dag's proxied state
        is None, then we assume the dag proxies at the task level. If the dag's proxied state is a boolean,
        then we assume the dag proxies at the dag level.
        """
        return self.dags[dag_id].dag_proxies_at_task_level

    def dag_proxies_at_dag_level(self, dag_id: str) -> bool:
        """Dags can proxy on either a task-by-task basis, or for the entire dag at once.
        We use the proxied state to determine which is the case for a given dag. If the dag's proxied state
        is None, then we assume the dag proxies at the task level. If the dag's proxied state is a boolean,
        then we assume the dag proxies at the dag level.
        """
        return self.dags[dag_id].dag_proxies_at_dag_level

    def get_proxied_dict_for_dag(
        self, dag_id: str
    ) -> Optional[Dict[str, Sequence[Dict[str, Any]]]]:
        if dag_id not in self.dags:
            return None
        return {
            "tasks": [
                {"proxied": task_state.proxied, "id": task_id}
                for task_id, task_state in self.dags[dag_id].tasks.items()
            ]
        }

    @staticmethod
    def from_dict(proxied_dict: Dict[str, Any]) -> "AirflowProxiedState":
        dags = {}
        for dag_id, dag_dict in proxied_dict.items():
            dags[dag_id] = DagProxiedState.from_dict(dag_dict)
        return AirflowProxiedState(dags=dags)


class ProxiedStateParsingError(Exception):
    pass


def load_proxied_state_from_yaml(proxied_yaml_path: Path) -> AirflowProxiedState:
    # Expect proxied_yaml_path to be a directory, where each file represents a dag, and each
    # file in the subdir represents a task. The dictionary for each task should contain two keys;
    # id: the task id, and proxied: a boolean indicating whether the task has been proxied.
    dag_proxied_states = {}
    try:
        for dag_file in proxied_yaml_path.iterdir():
            # Check that the file is a yaml file or yml file
            if dag_file.suffix not in [".yaml", ".yml"]:
                continue
            dag_id = dag_file.stem
            yaml_dict = yaml.safe_load(dag_file.read_text())
            if not isinstance(yaml_dict, dict):
                raise Exception("Expected a dictionary")
            dag_proxied_states[dag_id] = DagProxiedState.from_dict(yaml_dict)
    except Exception as e:
        raise ProxiedStateParsingError("Error parsing proxied state yaml") from e
    return AirflowProxiedState(dags=dag_proxied_states)