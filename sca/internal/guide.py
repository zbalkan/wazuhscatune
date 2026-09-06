import hashlib
import html
import os
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, TextIO

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from sca.config import VERSION
from sca.internal.loosening import Tailoring, TailoringException
from sca.internal.review import DecisionType
from sca.internal.sca import Compliance, SCA

ENCODING = 'UTF-8'


def escape_markdown(value: object) -> str:
    text = html.escape(str(value), quote=False).replace('\\', '\\\\')
    for character in '[]()#->*_`':
        text = text.replace(character, f'\\{character}')
    return text


def escape_markdown_cell(value: object) -> str:
    return (escape_markdown(value).replace('|', '\\|')
            .replace('\r\n', '<br>').replace('\n', '<br>').replace('\r', '<br>'))


def _sha256(path: str) -> str:
    with open(path, 'rb') as stream:
        return hashlib.sha256(stream.read()).hexdigest()


def _flatten_compliance(compliance: list[Compliance] | None) -> str:
    return '; '.join(
        f"{framework}: {', '.join(str(value) for value in values)}"
        for item in compliance or []
        for framework, values in item.items()
    )


def _write_markdown_table(stream: TextIO, title: str,
                          entries: list[dict[str, Any]]) -> None:
    stream.write(f"## {title}\n\n")
    stream.write("| Check ID | Check Name | Justification | Compliance |\n")
    stream.write("| --- | --- | --- | --- |\n")
    for entry in entries:
        compliance = _flatten_compliance(entry.get('compliance'))
        stream.write(
            f"| {entry['check_id']} | {escape_markdown_cell(entry['title'])} | "
            f"{escape_markdown_cell(entry['justification'])} | "
            f"{escape_markdown_cell(compliance)} |\n"
        )
    stream.write("\n")


class Guide:
    def __init__(self, baseline_path: str) -> None:
        self.baseline_path = baseline_path
        self.__yaml__ = YAML()
        with open(baseline_path, mode='r', encoding=ENCODING) as stream:
            self.__sca_yml__ = CommentedMap(self.__yaml__.load(stream))
        self.sca = SCA.from_dict(self.__sca_yml__)

    def export_custom(self, tailoring: Tailoring, custom_path: str) -> None:
        custom = deepcopy(self.__sca_yml__)
        policy = custom['policy']
        policy['name'] = tailoring.name
        policy['id'] = tailoring.id
        policy['description'] = tailoring.description
        policy['file'] = os.path.basename(custom_path)
        custom['checks'][:] = [
            check for check in custom['checks']
            if check.get('id') not in tailoring.decisions
        ]
        with open(custom_path, mode='w', encoding=ENCODING) as stream:
            self.__yaml__.dump(custom, stream)

    @staticmethod
    def _record_entry(check_id: int,
                      decision: TailoringException) -> dict[str, Any]:
        entry: dict[str, Any] = {
            'check_id': check_id,
            'title': decision.exception_check.title,
            'justification': decision.justification,
        }
        if decision.exception_check.compliance is not None:
            entry['compliance'] = deepcopy(decision.exception_check.compliance)
        return entry

    def export_exceptions(self, tailoring: Tailoring, tailored_path: str,
                          yml_path: str, md_path: str,
                          generated_at: str | None = None) -> None:
        sca = self.sca
        baseline_digest = _sha256(self.baseline_path)
        tailored_digest = _sha256(tailored_path)
        decisions = sorted(tailoring.decisions.items())
        exceptions = [
            self._record_entry(check_id, decision)
            for check_id, decision in decisions
            if decision.decision is DecisionType.EXCEPTION
        ]
        not_applicable = [
            self._record_entry(check_id, decision)
            for check_id, decision in decisions
            if decision.decision is DecisionType.NOT_APPLICABLE
        ]

        record = {
            'baseline': {
                'name': sca.policy.name,
                'id': sca.policy.id,
                'file': sca.policy.file,
                'sha256': baseline_digest,
            },
            'tailored_policy': {
                'name': tailoring.name,
                'id': tailoring.id,
                'file': os.path.basename(tailored_path),
                'sha256': tailored_digest,
            },
            'generated_by': {'tool': 'wazuhscatune', 'version': VERSION},
            'generated_at': generated_at or datetime.now(timezone.utc).isoformat(),
            'exceptions': exceptions,
            'not_applicable': not_applicable,
        }

        with open(yml_path, mode='w', encoding=ENCODING) as stream:
            self.__yaml__.dump(record, stream)

        with open(md_path, mode='w', encoding=ENCODING) as stream:
            stream.write(f"# {escape_markdown(tailoring.name)} Exception Record\n\n")
            stream.write(
                f"## {escape_markdown(tailoring.name)} "
                f"({escape_markdown(tailoring.id)})\n\n"
            )
            stream.write(f"{escape_markdown(tailoring.description)}\n\n")
            stream.write(
                f"Baseline: {escape_markdown(sca.policy.name)} "
                f"(`{escape_markdown(sca.policy.id)}`)  \n"
                f"SHA-256: `{baseline_digest}`\n\n"
            )
            _write_markdown_table(stream, 'Exceptions', exceptions)
            _write_markdown_table(stream, 'Not Applicable', not_applicable)
            stream.write(
                "## Notes\n\nGenerated by `wazuhscatune`. "
                "Update the exception record and tailored policy together.\n"
            )
