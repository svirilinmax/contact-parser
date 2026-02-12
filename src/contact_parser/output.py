import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class ResultSaver:
    """Класс для сохранения результатов парсинга"""

    @staticmethod
    def save_single_result(result: Dict[str, Any], output_path: Path) -> None:
        """
        Сохраняет один результат в файл

        Args:
            result: Результат парсинга
            output_path: Путь к файлу
        """
        # Создаем директорию если её нет
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Добавляем метаданные
        result_with_meta = result.copy()
        result_with_meta["_metadata"] = {
            "generated_at": datetime.now().isoformat(),
            "parser_version": "2.0.0",
        }

        # Сохраняем в JSON
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result_with_meta, f, ensure_ascii=False, indent=2)

    @staticmethod
    def save_batch_results(results: List[Dict[str, Any]], output_dir: Path) -> None:
        """
        Сохраняет результаты пакетной обработки

        Args:
            results: Список результатов
            output_dir: Директория для сохранения
        """
        # Создаем директорию если её нет
        output_dir.mkdir(parents=True, exist_ok=True)

        # Сохраняем каждый результат в отдельный файл
        for i, result in enumerate(results):
            # Создаем имя файла
            if result.get("success", False):
                url = result.get("url", f"result_{i + 1}")
                # Извлекаем домен из URL
                from urllib.parse import urlparse

                parsed_url = urlparse(url)
                domain = parsed_url.netloc
                if domain:
                    filename = f"{domain.replace('.', '_')}_{i + 1}.json"
                else:
                    filename = f"result_{i + 1}.json"
            else:
                filename = f"error_{i + 1}.json"

            filepath = output_dir / filename
            ResultSaver.save_single_result(result, filepath)

        # Также сохраняем сводный файл
        summary = {
            "total": len(results),
            "successful": sum(1 for r in results if r.get("success", False)),
            "failed": sum(1 for r in results if not r.get("success", False)),
            "results": [
                {
                    "url": r.get("url", ""),
                    "success": r.get("success", False),
                    "email_count": len(r.get("emails", [])),
                    "phone_count": len(r.get("phones", [])),
                }
                for r in results
            ],
            "_metadata": {
                "generated_at": datetime.now().isoformat(),
                "parser_version": "2.0.0",
            },
        }

        summary_file = output_dir / "summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

    @staticmethod
    def save_to_directory(result: Dict[str, Any], output_dir: Path, filename: str = None) -> Path:
        """
        Сохраняет результат в указанную директорию

        Args:
            result: Результат парсинга
            output_dir: Директория для сохранения
            filename: Имя файла (если None, генерируется автоматически)

        Returns:
            Path к сохраненному файлу
        """
        # Создаем директорию если её нет
        output_dir.mkdir(parents=True, exist_ok=True)

        # Генерируем имя файла если не указано
        if filename is None:
            url = result.get("url", "result")
            from urllib.parse import urlparse

            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            if domain:
                filename = f"{domain.replace('.', '_')}_contacts.json"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"contacts_{timestamp}.json"

        filepath = output_dir / filename
        ResultSaver.save_single_result(result, filepath)

        return filepath
