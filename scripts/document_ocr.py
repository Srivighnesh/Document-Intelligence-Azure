"""Run Azure Document Intelligence OCR for a local file or URL."""

import argparse

from src import config
from src.models.result_writer import ResultWriter
from src.services.document_intelligence import DocumentAnalyzer


def main() -> None:
    """Analyze the input document and save its OCR result."""
    parser = argparse.ArgumentParser(
        description="Extract OCR text with Azure Document Intelligence."
    )
    parser.add_argument("document", help="Local document path or document URL.")
    parser.add_argument(
        "--model-id",
        default=config.DOCUMENT_INTELLIGENCE_MODEL_ID,
        help="Analysis model ID.",
    )
    arguments = parser.parse_args()

    analyzer = DocumentAnalyzer(
        endpoint=config.DOCUMENT_INTELLIGENCE_ENDPOINT,
        key=config.DOCUMENT_INTELLIGENCE_KEY,
    )
    result = analyzer.analyze(arguments.document, arguments.model_id)
    output_path = ResultWriter().write(result, arguments.document, arguments.model_id)
    print(f"OCR result saved to: {output_path}")


if __name__ == "__main__":
    main()
