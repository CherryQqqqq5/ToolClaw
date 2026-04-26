# ToolSandbox Data Coverage Audit (2026-04-26)

## Summary

This audit separates the official ToolSandbox scenario inventory from the repository's current frozen official-run export. The inventory is candidate-space provenance only; it is not experimental evidence.

- official inventory scenarios: `1032`
- current frozen export rows: `88`
- inventory scenarios included in frozen export: `88`
- inventory scenarios not included in frozen export: `944`
- coverage rate: `0.0853`
- rapidapi/external-api scenarios: `523`
- unmatched frozen export rows: `0`

Safe wording: evaluate on a frozen ToolSandbox official-run export subset, with coverage audited against the official scenario inventory. Do not call the current frozen export a complete official ToolSandbox benchmark.

## Three-Layer Evidence Model

1. Layer 1: official scenario inventory. Scenario source coverage only; not evidence.
2. Layer 2: official-run export. Actual ToolSandbox result summaries and trajectories; can support official-run claims within documented coverage.
3. Layer 3: derived mechanism suites. Targeted ToolSandbox-derived evaluations such as semantic repair, planner-sensitive, and reuse suites.

## Category Coverage

| category | inventory count | missing from frozen export |
| --- | ---: | ---: |
| `MULTIPLE_TOOL_CALL` | 656 | 585 |
| `THREE_DISTRACTION_TOOLS` | 645 | 645 |
| `SINGLE_USER_TURN` | 584 | 523 |
| `CANONICALIZATION` | 472 | 426 |
| `MULTIPLE_USER_TURN` | 224 | 199 |
| `INSUFFICIENT_INFORMATION` | 224 | 222 |
| `STATE_DEPENDENCY` | 192 | 176 |
| `SINGLE_TOOL_CALL` | 152 | 137 |
| `NO_DISTRACTION_TOOLS` | 129 | 41 |
| `TEN_DISTRACTION_TOOLS` | 129 | 129 |
| `ARG_DESCRIPTION_SCRAMBLED` | 129 | 129 |
| `ARG_TYPE_SCRAMBLED` | 129 | 129 |
| `TOOL_DESCRIPTION_SCRAMBLED` | 129 | 129 |
| `TOOL_NAME_SCRAMBLED` | 129 | 129 |
| `ALL_TOOLS_AVAILABLE` | 129 | 129 |

## External API / RapidAPI Risk

| dependency reason | scenario count |
| --- | ---: |
| `rapidapi_backed_tools:convert_currency,search_lat_lon,search_location_around_lat_lon,search_stock,search_weather_around_lat_lon` | 174 |
| `rapidapi_backed_tools:search_location_around_lat_lon` | 85 |
| `rapidapi_backed_tools:search_lat_lon,search_location_around_lat_lon,search_stock` | 61 |
| `rapidapi_backed_tools:search_lat_lon,search_location_around_lat_lon,search_stock,search_weather_around_lat_lon` | 53 |
| `rapidapi_backed_tools:search_location_around_lat_lon,search_weather_around_lat_lon` | 31 |
| `rapidapi_backed_tools:convert_currency` | 25 |
| `rapidapi_backed_tools:search_lat_lon,search_stock,search_weather_around_lat_lon` | 25 |
| `rapidapi_backed_tools:search_lat_lon` | 17 |
| `rapidapi_backed_tools:search_lat_lon,search_location_around_lat_lon,search_weather_around_lat_lon` | 15 |
| `rapidapi_backed_tools:convert_currency,search_lat_lon,search_location_around_lat_lon,search_weather_around_lat_lon` | 10 |
| `rapidapi_backed_tools:search_location_around_lat_lon,search_stock` | 10 |
| `rapidapi_backed_tools:search_weather_around_lat_lon` | 6 |
| `rapidapi_backed_tools:convert_currency,search_lat_lon` | 4 |
| `rapidapi_backed_tools:search_stock` | 3 |
| `rapidapi_backed_tools:convert_currency,search_lat_lon,search_location_around_lat_lon` | 2 |
| `rapidapi_backed_tools:convert_currency,search_location_around_lat_lon` | 1 |
| `rapidapi_backed_tools:convert_currency,search_location_around_lat_lon,search_weather_around_lat_lon` | 1 |

## Legacy Frozen Export Boundary

`data/toolsandbox.formal.official.json` remains useful as a legacy frozen official-run subset, but it should not be described as the complete official ToolSandbox scenario space. Future official claims should either use a core reproducible export with documented exclusions or a full available export with API configuration and coverage ledger.

## Claim Impact

- No ToolSandbox claim is promoted by this audit.
- Existing derived mechanism suites keep their own provenance and should not be described as complete official ToolSandbox benchmark results.
- Reuse v3, semantic repair v2, and any future official core/full rerun should consume this coverage ledger before formal evidence is claimed.

## External/API Missing Examples

| scenario | reason |
| --- | --- |
| `add_contact_with_name_and_phone_number_10_distraction_tools` | `rapidapi_backed_tools:convert_currency,search_location_around_lat_lon` |
| `add_contact_with_name_and_phone_number_all_tools` | `rapidapi_backed_tools:convert_currency,search_lat_lon,search_location_around_lat_lon,search_stock,search_weather_around_lat_lon` |
| `add_reminder_content_and_date_and_time_all_tools` | `rapidapi_backed_tools:convert_currency,search_lat_lon,search_location_around_lat_lon,search_stock,search_weather_around_lat_lon` |
| `add_reminder_content_and_date_and_time_alt_all_tools` | `rapidapi_backed_tools:convert_currency,search_lat_lon,search_location_around_lat_lon,search_stock,search_weather_around_lat_lon` |
| `add_reminder_content_and_date_and_time_multiple_user_turn_all_tools` | `rapidapi_backed_tools:convert_currency,search_lat_lon,search_location_around_lat_lon,search_stock,search_weather_around_lat_lon` |
| `add_reminder_content_and_date_and_time_multiple_user_turn_alt_all_tools` | `rapidapi_backed_tools:convert_currency,search_lat_lon,search_location_around_lat_lon,search_stock,search_weather_around_lat_lon` |
| `add_reminder_content_and_week_delta_and_time_10_distraction_tools` | `rapidapi_backed_tools:convert_currency` |
| `add_reminder_content_and_week_delta_and_time_all_tools` | `rapidapi_backed_tools:convert_currency,search_lat_lon,search_location_around_lat_lon,search_stock,search_weather_around_lat_lon` |
| `add_reminder_content_and_week_delta_and_time_alt_10_distraction_tools` | `rapidapi_backed_tools:convert_currency` |
| `add_reminder_content_and_week_delta_and_time_alt_all_tools` | `rapidapi_backed_tools:convert_currency,search_lat_lon,search_location_around_lat_lon,search_stock,search_weather_around_lat_lon` |
| `add_reminder_content_and_week_delta_and_time_and_location_10_distraction_tools` | `rapidapi_backed_tools:convert_currency,search_lat_lon,search_location_around_lat_lon,search_stock,search_weather_around_lat_lon` |
| `add_reminder_content_and_week_delta_and_time_and_location_3_distraction_tools` | `rapidapi_backed_tools:search_lat_lon,search_location_around_lat_lon,search_stock` |
| `add_reminder_content_and_week_delta_and_time_and_location_3_distraction_tools_arg_description_scrambled` | `rapidapi_backed_tools:search_lat_lon,search_location_around_lat_lon,search_stock` |
| `add_reminder_content_and_week_delta_and_time_and_location_3_distraction_tools_arg_type_scrambled` | `rapidapi_backed_tools:search_lat_lon,search_location_around_lat_lon,search_stock` |
| `add_reminder_content_and_week_delta_and_time_and_location_3_distraction_tools_tool_description_scrambled` | `rapidapi_backed_tools:search_lat_lon,search_location_around_lat_lon,search_stock` |
| `add_reminder_content_and_week_delta_and_time_and_location_3_distraction_tools_tool_name_scrambled` | `rapidapi_backed_tools:search_lat_lon,search_location_around_lat_lon,search_stock` |
| `add_reminder_content_and_week_delta_and_time_and_location_all_tools` | `rapidapi_backed_tools:convert_currency,search_lat_lon,search_location_around_lat_lon,search_stock,search_weather_around_lat_lon` |
| `add_reminder_content_and_week_delta_and_time_and_location_alt_10_distraction_tools` | `rapidapi_backed_tools:convert_currency,search_lat_lon,search_location_around_lat_lon,search_stock,search_weather_around_lat_lon` |
| `add_reminder_content_and_week_delta_and_time_and_location_alt_3_distraction_tools` | `rapidapi_backed_tools:search_lat_lon,search_location_around_lat_lon,search_stock` |
| `add_reminder_content_and_week_delta_and_time_and_location_alt_3_distraction_tools_arg_description_scrambled` | `rapidapi_backed_tools:search_lat_lon,search_location_around_lat_lon,search_stock` |
