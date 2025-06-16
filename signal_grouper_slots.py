# Define the range of banks
num_banks = 1  # Adjust this to generate more slots (up to 19 slots as per your original request)

# Define the range of banks
num_entries = 20  # Adjust this to generate more slots (up to 19 slots as per your original request)

# Parent group
parent_group = 644
parent_name = "Issue Unit"

# Group
initial_session_group = parent_group + 1
base_group_base_name = "Slot "


# Wave name
wave_name = "Wave.1"

#signal_prefix = 'TestDriver.testHarness.chiptop.system.tile_prci_domain.tile_reset_domain.boom_tile.core.int_issue_unit.issue_slots'
signal_prefix = 'TestDriver.testHarness.chiptop.system.tile_prci_domain.tile_reset_domain.boom_tile.core.int_issue_unit.issue_slots'

# Base template for generating the code
base_signal = [
'''{signal_prefix}_{entry}_valid \
{signal_prefix}_{entry}_will_be_valid \
{signal_prefix}_{entry}_request \
{signal_prefix}_{entry}_grant \
{signal_prefix}_{entry}_in_uop_valid \
{signal_prefix}_{entry}_uop_taint \
{signal_prefix}_{entry}_uop_yrot''',

'''{signal_prefix}_{entry}_uop_uopc \
{signal_prefix}_{entry}_uop_rob_idx \
{signal_prefix}_{entry}_uop_pc_lob \
{signal_prefix}_{entry}_uop_fu_code \
{signal_prefix}_{entry}_uop_ftq_idx \
{signal_prefix}_{entry}_uop_is_br \
{signal_prefix}_{entry}_uop_taken \
{signal_prefix}_{entry}_uop_is_sfb \
{signal_prefix}_{entry}_uop_is_rvc \
{signal_prefix}_{entry}_uop_is_jalr \
{signal_prefix}_{entry}_uop_is_jal \
{signal_prefix}_{entry}_uop_is_amo''',

'''{signal_prefix}_{entry}_uop_prs1 \
{signal_prefix}_{entry}_uop_lrs1_rtype \
{signal_prefix}_{entry}_uop_prs2 \
{signal_prefix}_{entry}_uop_lrs2_rtype \
{signal_prefix}_{entry}_uop_pdst \
{signal_prefix}_{entry}_uop_dst_rtype \
{signal_prefix}_{entry}_uop_ldst_val \
{signal_prefix}_{entry}_uop_uses_stq \
{signal_prefix}_{entry}_uop_mem_cmd \
{signal_prefix}_{entry}_uop_ldq_idx \
{signal_prefix}_{entry}_uop_iw_p2_poisoned \
{signal_prefix}_{entry}_uop_iw_p1_poisoned \
{signal_prefix}_{entry}_uop_imm_packed \
{signal_prefix}_{entry}_uop_fp_val \
{signal_prefix}_{entry}_uop_edge_inst \
{signal_prefix}_{entry}_uop_bypassable \
{signal_prefix}_{entry}_uop_br_tag \
{signal_prefix}_{entry}_uop_br_mask'''
]


base_group = '''gui_list_add_group -id ${{{wave_name}}} -after {{{parent_name}|{base_group_base_name}{idx:02d}}} {{{{{parent_name}|{base_group_base_name}{next_idx:02d}}}}}'''

# Function to generate the script for each slot
def generate_groups_and_signals(idx):
    code = f'''# {base_group_base_name} {idx:02d}
set _session_group_{initial_session_group + idx} $_session_group_{parent_group}|
append _session_group_{initial_session_group + idx} {{{base_group_base_name}{idx:02d}}}
gui_sg_create "$_session_group_{initial_session_group + idx}"
set {{{parent_name}|{base_group_base_name}{idx:02d}}} "$_session_group_{initial_session_group + idx}"

gui_sg_addsignal -group "$_session_group_{initial_session_group + idx}" {{ {base_signal[0].format(signal_prefix=signal_prefix, entry=idx)} }}
gui_sg_addsignal -group "$_session_group_{initial_session_group + idx}" {{ Divider }} -divider
gui_sg_addsignal -group "$_session_group_{initial_session_group + idx}" {{ {base_signal[1].format(signal_prefix=signal_prefix, entry=idx)} }}
gui_sg_addsignal -group "$_session_group_{initial_session_group + idx}" {{ Divider }} -divider
gui_sg_addsignal -group "$_session_group_{initial_session_group + idx}" {{ {base_signal[2].format(signal_prefix=signal_prefix, entry=idx)} }}

'''
    return code

# Generate and print the code for all slots
print('### Signals to groups')
for e in range(num_entries):
    #print("b: {b}    e:{e}   idx:{idx:02d}".format(b=b, e=e, idx=idx))
    print(generate_groups_and_signals(e))

print('### Groups')

print("gui_list_add_group -id ${{{wave_name}}} -after {{{parent_name}}} {{{{{parent_name}|{base_group_base_name}{idx:02d}}}}}".format(wave_name=wave_name, parent_name=parent_name, base_group_base_name=base_group_base_name, idx=0))
for e in range(num_entries-1):

    print(base_group.format(wave_name=wave_name, parent_name=parent_name, base_group_base_name=base_group_base_name, idx=e, next_idx=e+1))

print('\n#Done.')
