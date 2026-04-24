# Planner-Sensitive Family Diagnostics

## `branch_select_execute`

- `a1_recovery`: success=0.0, classifications={'capability_intent_gap': 33}, recommended_fix_scope={'capability_intent_rules': 33}
- example `planner_sensitive_branch_select_execute_01` run=1: classification=capability_intent_gap, fix=capability_intent_rules, expected_caps=['cap_retrieve', 'cap_select', 'cap_modify', 'cap_verify'], actual_caps=['cap_retrieve', 'cap_write'], expected_tools=['context_retriever', 'branch_selector', 'branch_executor', 'result_verifier'], actual_tools=['search_tool', 'write_tool']
- example `planner_sensitive_branch_select_execute_02` run=1: classification=capability_intent_gap, fix=capability_intent_rules, expected_caps=['cap_retrieve', 'cap_select', 'cap_modify', 'cap_verify'], actual_caps=['cap_retrieve', 'cap_write'], expected_tools=['context_retriever', 'branch_selector', 'branch_executor', 'result_verifier'], actual_tools=['search_tool', 'write_tool']
- example `planner_sensitive_branch_select_execute_03` run=1: classification=capability_intent_gap, fix=capability_intent_rules, expected_caps=['cap_retrieve', 'cap_select', 'cap_modify', 'cap_verify'], actual_caps=['cap_retrieve', 'cap_write'], expected_tools=['context_retriever', 'branch_selector', 'branch_executor', 'result_verifier'], actual_tools=['search_tool', 'write_tool']
- `a2_planner`: success=1.0, classifications={}, recommended_fix_scope={}
- `a3_interaction`: success=1.0, classifications={}, recommended_fix_scope={}
- `a4_reuse`: success=1.0, classifications={}, recommended_fix_scope={}

## `check_modify_verify`

- `a1_recovery`: success=0.0, classifications={'capability_intent_gap': 33}, recommended_fix_scope={'capability_intent_rules': 33}
- example `planner_sensitive_check_modify_verify_01` run=1: classification=capability_intent_gap, fix=capability_intent_rules, expected_caps=['cap_check', 'cap_modify', 'cap_verify'], actual_caps=['cap_retrieve', 'cap_write'], expected_tools=['state_checker', 'state_modifier', 'change_verifier'], actual_tools=['search_tool', 'write_tool']
- example `planner_sensitive_check_modify_verify_02` run=1: classification=capability_intent_gap, fix=capability_intent_rules, expected_caps=['cap_check', 'cap_modify', 'cap_verify'], actual_caps=['cap_retrieve', 'cap_write'], expected_tools=['state_checker', 'state_modifier', 'change_verifier'], actual_tools=['search_tool', 'write_tool']
- example `planner_sensitive_check_modify_verify_03` run=1: classification=capability_intent_gap, fix=capability_intent_rules, expected_caps=['cap_check', 'cap_modify', 'cap_verify'], actual_caps=['cap_retrieve', 'cap_write'], expected_tools=['state_checker', 'state_modifier', 'change_verifier'], actual_tools=['search_tool', 'write_tool']
- `a2_planner`: success=1.0, classifications={}, recommended_fix_scope={}
- `a3_interaction`: success=1.0, classifications={}, recommended_fix_scope={}
- `a4_reuse`: success=1.0, classifications={}, recommended_fix_scope={}

## `multi_source_merge_write`

- `a1_recovery`: success=0.0, classifications={'capability_intent_gap': 33}, recommended_fix_scope={'capability_intent_rules': 33}
- example `planner_sensitive_multi_source_merge_write_01` run=1: classification=capability_intent_gap, fix=capability_intent_rules, expected_caps=['cap_retrieve', 'cap_merge', 'cap_write'], actual_caps=['cap_retrieve', 'cap_write'], expected_tools=['primary_source_fetcher', 'secondary_source_fetcher', 'source_merger', 'merged_report_writer'], actual_tools=['search_tool', 'write_tool']
- example `planner_sensitive_multi_source_merge_write_02` run=1: classification=capability_intent_gap, fix=capability_intent_rules, expected_caps=['cap_retrieve', 'cap_merge', 'cap_write'], actual_caps=['cap_retrieve', 'cap_write'], expected_tools=['primary_source_fetcher', 'secondary_source_fetcher', 'source_merger', 'merged_report_writer'], actual_tools=['search_tool', 'write_tool']
- example `planner_sensitive_multi_source_merge_write_03` run=1: classification=capability_intent_gap, fix=capability_intent_rules, expected_caps=['cap_retrieve', 'cap_merge', 'cap_write'], actual_caps=['cap_retrieve', 'cap_write'], expected_tools=['primary_source_fetcher', 'secondary_source_fetcher', 'source_merger', 'merged_report_writer'], actual_tools=['search_tool', 'write_tool']
- `a2_planner`: success=0.0, classifications={'binder_selection_gap': 33}, recommended_fix_scope={'binder_rules': 33}
- example `planner_sensitive_multi_source_merge_write_01` run=1: classification=binder_selection_gap, fix=binder_rules, expected_caps=['cap_retrieve', 'cap_merge', 'cap_write'], actual_caps=['cap_retrieve', 'cap_merge', 'cap_write'], expected_tools=['primary_source_fetcher', 'secondary_source_fetcher', 'source_merger', 'merged_report_writer'], actual_tools=['primary_source_fetcher']
- example `planner_sensitive_multi_source_merge_write_02` run=1: classification=binder_selection_gap, fix=binder_rules, expected_caps=['cap_retrieve', 'cap_merge', 'cap_write'], actual_caps=['cap_retrieve', 'cap_merge', 'cap_write'], expected_tools=['primary_source_fetcher', 'secondary_source_fetcher', 'source_merger', 'merged_report_writer'], actual_tools=['primary_source_fetcher']
- example `planner_sensitive_multi_source_merge_write_03` run=1: classification=binder_selection_gap, fix=binder_rules, expected_caps=['cap_retrieve', 'cap_merge', 'cap_write'], actual_caps=['cap_retrieve', 'cap_merge', 'cap_write'], expected_tools=['primary_source_fetcher', 'secondary_source_fetcher', 'source_merger', 'merged_report_writer'], actual_tools=['primary_source_fetcher']
- `a3_interaction`: success=1.0, classifications={}, recommended_fix_scope={}
- `a4_reuse`: success=1.0, classifications={}, recommended_fix_scope={}

## `retrieve_summarize_write`

- `a1_recovery`: success=0.0, classifications={'capability_intent_gap': 27}, recommended_fix_scope={'capability_intent_rules': 27}
- example `planner_sensitive_retrieve_summarize_write_01` run=1: classification=capability_intent_gap, fix=capability_intent_rules, expected_caps=['cap_retrieve', 'cap_summarize', 'cap_write'], actual_caps=['cap_retrieve', 'cap_write'], expected_tools=['source_lookup', 'summary_builder', 'report_writer'], actual_tools=['search_tool', 'write_tool']
- example `planner_sensitive_retrieve_summarize_write_02` run=1: classification=capability_intent_gap, fix=capability_intent_rules, expected_caps=['cap_retrieve', 'cap_summarize', 'cap_write'], actual_caps=['cap_retrieve', 'cap_write'], expected_tools=['source_lookup', 'summary_builder', 'report_writer'], actual_tools=['search_tool', 'write_tool']
- example `planner_sensitive_retrieve_summarize_write_03` run=1: classification=capability_intent_gap, fix=capability_intent_rules, expected_caps=['cap_retrieve', 'cap_summarize', 'cap_write'], actual_caps=['cap_retrieve', 'cap_write'], expected_tools=['source_lookup', 'summary_builder', 'report_writer'], actual_tools=['search_tool', 'write_tool']
- `a2_planner`: success=1.0, classifications={}, recommended_fix_scope={}
- `a3_interaction`: success=1.0, classifications={}, recommended_fix_scope={}
- `a4_reuse`: success=1.0, classifications={}, recommended_fix_scope={}

