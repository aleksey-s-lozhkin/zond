import json

from pathlib import Path

from zond.models.inspection import Inspection


class JsonStorage:
    """Сохранение и загрузка результатов проверки."""

    @staticmethod
    def save(
            inspection: Inspection,
            path: Path,
    ) -> None:
        """Сохранить проверку в JSON."""

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
                "w",
                encoding="utf-8",
        ) as file:
            json.dump(
                inspection.to_dict(),
                file,
                ensure_ascii=False,
                indent=4,
            )