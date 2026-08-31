from __future__ import annotations

from html import escape

from .guided_contracts import (
    ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH,
    ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH,
    REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH,
    REVIEW_RESULT_DOWNLOAD_ROUTE_PATH,
)
from .result_presentation import (
    BrowserSafeResultPresentationV1,
    ResultSectionV1,
    ResultTableV1,
)


def _details(values) -> str:
    if not values:
        return ""
    return (
        '<dl class="result-details">'
        + "".join(
            f"<dt>{escape(detail.label)}</dt><dd>{escape(detail.value)}</dd>" for detail in values
        )
        + "</dl>"
    )


def _items(values) -> str:
    if not values:
        return ""
    return (
        '<ul class="result-list">'
        + "".join(f"<li>{escape(value)}</li>" for value in values)
        + "</ul>"
    )


def _table(table: ResultTableV1) -> str:
    headings = "".join(f'<th scope="col">{escape(column)}</th>' for column in table.columns)
    rows = "".join(
        "<tr>"
        + "".join(
            (f'<th scope="row">{escape(cell)}</th>' if index == 0 else f"<td>{escape(cell)}</td>")
            for index, cell in enumerate(row)
        )
        + "</tr>"
        for row in table.rows
    )
    return (
        '<div class="result-table-wrap"><table>'
        f"<caption>{escape(table.caption)}</caption>"
        f"<thead><tr>{headings}</tr></thead><tbody>{rows}</tbody>"
        "</table></div>"
    )


def _section_body(section: ResultSectionV1) -> str:
    return (
        "".join(f"<p>{escape(paragraph)}</p>" for paragraph in section.paragraphs)
        + _details(section.details)
        + _items(section.items)
        + "".join(_table(table) for table in section.tables)
    )


def _download_links(
    *,
    page: str,
    request_download_available: bool,
    result_download_available: bool,
) -> str:
    if page == "analyze":
        request_href = ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH
        result_href = ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH
    else:
        request_href = REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH
        result_href = REVIEW_RESULT_DOWNLOAD_ROUTE_PATH
    links = []
    if request_download_available:
        links.append(
            f'<li><a href="{escape(request_href, quote=True)}" '
            "download>Download exact Request JSON</a></li>"
        )
    if result_download_available:
        links.append(
            f'<li><a href="{escape(result_href, quote=True)}" '
            "download>Download exact Result JSON</a></li>"
        )
    if not links:
        return ""
    return '<nav aria-label="Result downloads"><ul>' + "".join(links) + "</ul></nav>"


def render_result_presentation_v1(
    presentation: BrowserSafeResultPresentationV1,
    *,
    request_download_available: bool = False,
    result_download_available: bool = False,
    page: str | None = None,
) -> str:
    """Renders one browser-safe Result projection as semantic escaped HTML."""

    if type(presentation) is not BrowserSafeResultPresentationV1:
        raise ValueError("presentation must be an exact browser-safe Result presentation.")
    if type(request_download_available) is not bool:
        raise ValueError("request_download_available must be a boolean.")
    if type(result_download_available) is not bool:
        raise ValueError("result_download_available must be a boolean.")
    effective_page = page or (
        "analyze" if presentation.workflow == "position_analysis" else "review"
    )
    if effective_page not in {"analyze", "review"}:
        raise ValueError("page must be 'analyze' or 'review'.")

    rendered = []
    for index, section in enumerate(presentation.sections):
        identifier = f"result-section-{index + 1}"
        body = _section_body(section)
        if index == 0 and presentation.warnings:
            body = (
                '<aside aria-label="Result warnings"><h3>Warnings</h3>'
                + _items(presentation.warnings)
                + "</aside>"
                + body
            )
        if section.title == "Technical details":
            body = (
                "<details><summary>Show Technical details</summary>"
                + body
                + _download_links(
                    page=effective_page,
                    request_download_available=request_download_available,
                    result_download_available=result_download_available,
                )
                + "</details>"
            )
        rendered.append(
            f'<section aria-labelledby="{identifier}">'
            f'<h2 id="{identifier}">{escape(section.title)}</h2>{body}</section>'
        )
    return '<div class="result-presentation">' + "".join(rendered) + "</div>"


def render_safe_result_error_summary_v1(*, title: str, message: str) -> str:
    """Renders a minimized escaped error summary outside normal Result states."""

    if type(title) is not str or not title or type(message) is not str or not message:
        raise ValueError("Safe Result error title and message must be non-empty text.")
    return (
        '<section class="result-error" aria-labelledby="result-error-heading">'
        f'<h2 id="result-error-heading">{escape(title)}</h2>'
        f"<p>{escape(message)}</p></section>"
    )
