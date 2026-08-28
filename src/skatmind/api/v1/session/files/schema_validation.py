from skatmind.api.v1.session.schema_validation import _validate_session_definition


def validate_session_file_result_document(document: object) -> None:
    _validate_session_definition(document, "session_file_api_result")
