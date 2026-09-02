from __future__ import annotations

import re
from html import escape

from .form_registry import FrontendFormDefinitionV1
from .translation_catalog import translate_frontend_message_v1
from .validation_contracts import FrontendSubmittedFormStateV1

_FORM_OPEN = re.compile(r"<form\b[^>]*>", re.IGNORECASE)
_DETAILS_OPEN = re.compile(r"<details\b[^>]*>", re.IGNORECASE)
_FORM_BLOCK = re.compile(r"(<form\b[^>]*>)(.*?)(</form>)", re.IGNORECASE | re.DOTALL)


def _attribute(tag: str, name: str) -> str | None:
    match = re.search(rf'\b{re.escape(name)}="([^"]*)"', tag, re.IGNORECASE)
    return None if match is None else match.group(1)


def _set_attribute(tag: str, name: str, value: str | None) -> str:
    pattern = re.compile(rf'\s+{re.escape(name)}(?:="[^"]*")?', re.IGNORECASE)
    tag = pattern.sub("", tag)
    if value is None:
        return tag
    return tag[:-1] + f' {name}="{escape(value, quote=True)}">'


def _find_form_bounds(
    html: str,
    definition: FrontendFormDefinitionV1,
    form_instance: int | None,
) -> tuple[int, int] | None:
    matching_index = 0
    for match in _FORM_OPEN.finditer(html):
        if _attribute(match.group(0), "action") != definition.action_route:
            continue
        end = html.find("</form>", match.end())
        if end < 0:
            continue
        end += len("</form>")
        block = html[match.start() : end]
        if definition.discriminator_field is not None:
            discriminator_field = re.escape(definition.discriminator_field)
            discriminator_value = re.escape(definition.discriminator_value or "")
            discriminator = re.compile(
                rf'<input\b(?=[^>]*\bname="{discriminator_field}")'
                rf'(?=[^>]*\bvalue="{discriminator_value}")[^>]*>',
                re.IGNORECASE,
            )
            if discriminator.search(block) is None:
                continue
        if form_instance is not None and matching_index != form_instance:
            matching_index += 1
            continue
        return match.start(), end
    return None


def instrument_registered_forms_v1(
    html: str,
    definitions: tuple[FrontendFormDefinitionV1, ...],
) -> str:
    """Adds opaque per-render ordinals only to unified URL-encoded forms."""

    counts: dict[str, int] = {}

    def instrument(match: re.Match[str]) -> str:
        opening, content, closing = match.groups()
        action = _attribute(opening, "action")
        candidates = tuple(
            definition
            for definition in definitions
            if definition.action_route == action
            and definition.media_type == "application/x-www-form-urlencoded"
        )
        if not candidates:
            return match.group(0)
        definition = candidates[0]
        for candidate in candidates:
            if candidate.discriminator_field is None:
                definition = candidate
                break
            discriminator = re.compile(
                rf'<input\b(?=[^>]*\bname="{re.escape(candidate.discriminator_field)}")'
                rf'(?=[^>]*\bvalue="{re.escape(candidate.discriminator_value or "")}")[^>]*>',
                re.IGNORECASE,
            )
            if discriminator.search(content) is not None:
                definition = candidate
                break
        instance = counts.get(definition.form_key, 0)
        counts[definition.form_key] = instance + 1
        metadata = f'<input type="hidden" name="_frontend_form_instance" value="{instance}">'
        return opening + metadata + content + closing

    return _FORM_BLOCK.sub(instrument, html)


def _open_containing_details(html: str, form_start: int, form_end: int) -> str:
    candidate = None
    for match in _DETAILS_OPEN.finditer(html, 0, form_start):
        candidate = match
    if candidate is None:
        return html
    close = html.find("</details>", candidate.end())
    if close < form_end or " open" in candidate.group(0):
        return html
    opened = candidate.group(0)[:-1] + " open>"
    return html[: candidate.start()] + opened + html[candidate.end() :]


def _replace_values(block: str, state: FrontendSubmittedFormStateV1) -> str:
    for entry in state.safe_visible_values.entries:
        field = re.escape(entry.field)
        values = entry.values

        input_pattern = re.compile(
            rf'<input\b(?=[^>]*\bname="{field}")[^>]*>',
            re.IGNORECASE,
        )

        def replace_input(
            match: re.Match[str],
            retained_values: tuple[str, ...] = values,
        ) -> str:
            tag = match.group(0)
            control_type = (_attribute(tag, "type") or "text").lower()
            if control_type in {"file", "hidden", "submit", "button"}:
                return tag
            if control_type in {"checkbox", "radio"}:
                submitted = _attribute(tag, "value") or "on"
                return _set_attribute(
                    tag,
                    "checked",
                    "checked" if submitted in retained_values else None,
                )
            return _set_attribute(tag, "value", retained_values[0])

        block = input_pattern.sub(replace_input, block)

        textarea_pattern = re.compile(
            rf'(<textarea\b(?=[^>]*\bname="{field}")[^>]*>).*?(</textarea>)',
            re.IGNORECASE | re.DOTALL,
        )
        block = textarea_pattern.sub(
            lambda match, retained_value=values[0]: (
                match.group(1) + escape(retained_value) + match.group(2)
            ),
            block,
        )

        select_pattern = re.compile(
            rf'(<select\b(?=[^>]*\bname="{field}")[^>]*>)(.*?)(</select>)',
            re.IGNORECASE | re.DOTALL,
        )
        select_index = 0

        def replace_select(
            match: re.Match[str],
            retained_values: tuple[str, ...] = values,
        ) -> str:
            nonlocal select_index
            options = re.sub(r"\s+selected(?:=\"selected\")?", "", match.group(2))
            retained_value = retained_values[min(select_index, len(retained_values) - 1)]
            select_index += 1
            selected = escape(retained_value, quote=True)
            option_pattern = re.compile(
                rf'(<option\b(?=[^>]*\bvalue="{re.escape(selected)}")[^>]*)(>)',
                re.IGNORECASE,
            )
            options = option_pattern.sub(r"\1 selected\2", options, count=1)
            return match.group(1) + options + match.group(3)

        block = select_pattern.sub(replace_select, block)
    return block


def _add_control_accessibility(
    block: str,
    field: str,
    described_by: str,
    control_id: str,
) -> tuple[str, str | None]:
    field_pattern = re.escape(field)
    patterns = (
        re.compile(rf'<input\b(?=[^>]*\bname="{field_pattern}")[^>]*>', re.IGNORECASE),
        re.compile(rf'<select\b(?=[^>]*\bname="{field_pattern}")[^>]*>', re.IGNORECASE),
        re.compile(rf'<textarea\b(?=[^>]*\bname="{field_pattern}")[^>]*>', re.IGNORECASE),
    )
    identifier_added = False
    first_control_id: str | None = None
    for pattern in patterns:

        def update(match: re.Match[str]) -> str:
            nonlocal first_control_id, identifier_added
            tag = _set_attribute(match.group(0), "aria-invalid", "true")
            if not identifier_added:
                first_control_id = _attribute(tag, "id") or control_id
                tag = _set_attribute(tag, "id", first_control_id)
                identifier_added = True
            existing = _attribute(tag, "aria-describedby")
            identifiers = tuple(dict.fromkeys((*(existing or "").split(), described_by)))
            return _set_attribute(tag, "aria-describedby", " ".join(identifiers))

        block = pattern.sub(update, block)
    return block, first_control_id


def apply_validation_feedback_to_html_v1(
    html: str,
    definition: FrontendFormDefinitionV1,
    state: FrontendSubmittedFormStateV1,
    *,
    locale: str,
    last_valid_result_retained: bool = False,
) -> str:
    """Applies locale-at-render-time feedback to one exact registered form."""

    if type(html) is not str or type(definition) is not FrontendFormDefinitionV1:
        raise ValueError("Validation rendering requires HTML and one registered form.")
    if type(state) is not FrontendSubmittedFormStateV1 or state.form_key != definition.form_key:
        raise ValueError("Submitted form state must match the registered form key.")
    bounds = _find_form_bounds(html, definition, state.form_instance)
    if bounds is None:
        return html
    form_start, form_end = bounds
    html = _open_containing_details(html, form_start, form_end)
    bounds = _find_form_bounds(html, definition, state.form_instance)
    if bounds is None:
        return html
    form_start, form_end = bounds
    block = _replace_values(html[form_start:form_end], state)
    translated: list[tuple[str | None, str, str]] = []
    field_messages: dict[str, list[tuple[str, str]]] = {}
    rendered_fields: dict[str, str] = {}
    field_definitions = {field.field_key: field for field in definition.safe_fields}
    for index, issue in enumerate(state.validation_issues, start=1):
        message = translate_frontend_message_v1(
            locale,
            issue.message_key,
            **issue.interpolation_values(),
        )
        message_id = f"validation-message-{state.feedback_generation}-{index}"
        translated.append((issue.field_key, message_id, message))
        if issue.field_key is not None:
            field_messages.setdefault(issue.field_key, []).append((message_id, message))
    for field, messages in field_messages.items():
        described_by = " ".join(identifier for identifier, _message in messages)
        control_id = f"validation-field-{state.feedback_generation}-{field}"
        block, rendered_control_id = _add_control_accessibility(
            block,
            field,
            described_by,
            control_id,
        )
        if rendered_control_id is None:
            continue
        rendered_fields[field] = rendered_control_id
        rendered_messages = "".join(
            f'<p class="field-error" id="{identifier}">{escape(message)}</p>'
            for identifier, message in messages
        )
        block = block.removesuffix("</form>") + rendered_messages + "</form>"

    heading_key = (
        "validation.summary.conflict_heading"
        if state.status == "conflict"
        else "validation.summary.heading"
    )
    guidance_key = (
        "validation.summary.conflict_guidance"
        if state.status == "conflict"
        else "validation.summary.guidance"
    )
    items = []
    form_anchor_id = f"validation-form-heading-{state.feedback_generation}"
    for field, _identifier, message in translated:
        href = f"#{rendered_fields.get(field or '', form_anchor_id)}"
        label = ""
        field_definition = field_definitions.get(field or "")
        if field_definition is not None:
            label = translate_frontend_message_v1(locale, field_definition.field_label_key) + ": "
        items.append(f'<li><a href="{escape(href, quote=True)}">{escape(label + message)}</a></li>')
    retained_result = (
        f"<p>{escape(translate_frontend_message_v1(locale, 'validation.last_valid_result'))}</p>"
        if last_valid_result_retained
        else ""
    )
    reload_guidance = (
        f"<p>{escape(translate_frontend_message_v1(locale, 'validation.reload_guidance'))}</p>"
        if state.status == "conflict"
        else ""
    )
    locale_attribute = escape(locale, quote=True)
    summary = (
        f'<section class="error-summary" role="alert" tabindex="-1" autofocus '
        f'aria-labelledby="validation-summary-heading-{state.feedback_generation}" '
        f'lang="{locale_attribute}">'
        f'<h2 id="validation-summary-heading-{state.feedback_generation}">'
        f"{escape(translate_frontend_message_v1(locale, heading_key))}</h2>"
        f"<p>{escape(translate_frontend_message_v1(locale, guidance_key))}</p>"
        f"<ul>{''.join(items)}</ul>{reload_guidance}{retained_result}</section>"
    )
    form_anchor = f'<span class="validation-anchor" id="{form_anchor_id}"></span>'
    block = form_anchor + block
    return html[:form_start] + summary + block + html[form_end:]
