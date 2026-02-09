import json
from datetime import datetime
from unittest.mock import patch

from contact_parser.output import ResultSaver


class TestResultSaver:
    """Тесты для сохранения результатов"""

    def test_save_single_result(self, tmp_path):
        """Тест сохранения одного результата"""

        result = {"url": "https://example.com", "emails": ["test@example.com"], "phones": ["+79991234567"]}

        output_path = tmp_path / "result.json"
        ResultSaver.save_single_result(result, output_path)

        assert output_path.exists()

        with open(output_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data["url"] == "https://example.com"
        assert saved_data["emails"] == ["test@example.com"]
        assert saved_data["phones"] == ["+79991234567"]
        assert "_metadata" in saved_data
        assert "generated_at" in saved_data["_metadata"]

    def test_save_single_result_creates_directory(self, tmp_path):
        """Тест создания директории при сохранении"""

        result = {"url": "https://example.com"}
        output_path = tmp_path / "deep" / "dir" / "result.json"

        assert not output_path.parent.exists()
        ResultSaver.save_single_result(result, output_path)

        assert output_path.parent.exists()
        assert output_path.exists()

    def test_save_batch_results(self, tmp_path):
        """Тест сохранения пакета результатов"""

        results = [
            {"url": "https://example.com", "success": True, "emails": ["test@example.com"], "phones": []},
            {"url": "https://test.org", "success": False, "emails": [], "phones": []},
        ]

        output_dir = tmp_path / "batch_results"
        ResultSaver.save_batch_results(results, output_dir)

        # Проверяем созданные файлы
        assert (output_dir / "example_com_1.json").exists()
        assert (output_dir / "error_2.json").exists()
        assert (output_dir / "summary.json").exists()

        # Проверяем summary
        with open(output_dir / "summary.json", "r", encoding="utf-8") as f:
            summary = json.load(f)

        assert summary["total"] == 2
        assert summary["successful"] == 1
        assert summary["failed"] == 1
        assert len(summary["results"]) == 2

    def test_save_to_directory_auto_filename(self, tmp_path):
        """Тест автоматического создания имени файла"""

        result = {"url": "https://example.com", "emails": ["test@example.com"], "phones": ["+79991234567"]}

        output_dir = tmp_path / "output"
        filepath = ResultSaver.save_to_directory(result, output_dir)

        assert filepath.exists()
        assert filepath.name == "example_com_contacts.json"

    def test_save_to_directory_custom_filename(self, tmp_path):
        """Тест сохранения с указанным именем файла"""

        result = {"url": "https://example.com"}
        output_dir = tmp_path / "output"

        filepath = ResultSaver.save_to_directory(result, output_dir, filename="custom.json")

        assert filepath.exists()
        assert filepath.name == "custom.json"

    def test_save_to_directory_no_url(self, tmp_path):
        """Тест сохранения без URL в результате"""

        result = {"emails": []}

        output_dir = tmp_path / "output"
        filepath = ResultSaver.save_to_directory(result, output_dir)

        assert filepath.exists()
        assert filepath.name.startswith("contacts_")
        assert filepath.name.endswith(".json")

    @patch("contact_parser.output.datetime")
    def test_save_to_directory_timestamp_fallback(self, mock_datetime, tmp_path):
        """Тест использования временной метки при отсутствии домена"""

        mock_now = datetime(2024, 1, 15, 10, 30, 0)
        mock_datetime.now.return_value = mock_now

        result = {"url": "not-a-valid-url"}

        output_dir = tmp_path / "output"
        filepath = ResultSaver.save_to_directory(result, output_dir)

        assert filepath.exists()
        assert filepath.name == "contacts_20240115_103000.json"
