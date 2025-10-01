# Define the range of banks
num_banks = 2  # Adjust this to generate more slots (up to 19 slots as per your original request)

# Define the range of banks
num_entries = 32  # Adjust this to generate more slots (up to 19 slots as per your original request)

# Group
initial_session_group = 159  # You can modify this to start at any group ID
base_group_base_name = "idx "

# Parent group
parent_group = 158
parent_name = "Entries"

# Wave name
wave_name = "Wave.1"

#signal_prefix = 'TestDriver.testHarness.chiptop.system.tile_prci_domain.tile_reset_domain.boom_tile.core.int_issue_unit.issue_slots'
signal_prefix = 'TestDriver.testHarness.chiptop.system.tile_prci_domain.tile_reset_domain.boom_tile.core.rob'

# Base template for generating the code
base_signal = '''{signal_prefix}.rob_val_{bank}_{entry} \
{signal_prefix}.rob_bsy_{bank}_{entry} \
{signal_prefix}.rob_unsafe_{bank}_{entry} \
{signal_prefix}.rob_exception_{bank}_{entry} \
{signal_prefix}.rob_predicated_{bank}_{entry} \
{signal_prefix}.rob_uop_{bank}_{entry}_uopc \
{signal_prefix}.rob_uop_{bank}_{entry}_is_rvc \
{signal_prefix}.rob_uop_{bank}_{entry}_is_br \
{signal_prefix}.rob_uop_{bank}_{entry}_is_jalr \
{signal_prefix}.rob_uop_{bank}_{entry}_is_jal \
{signal_prefix}.rob_uop_{bank}_{entry}_br_mask \
{signal_prefix}.rob_uop_{bank}_{entry}_ftq_idx \
{signal_prefix}.rob_uop_{bank}_{entry}_edge_inst \
{signal_prefix}.rob_uop_{bank}_{entry}_pc_lob \
{signal_prefix}.rob_uop_{bank}_{entry}_rob_idx \
{signal_prefix}.rob_uop_{bank}_{entry}_pdst \
{signal_prefix}.rob_uop_{bank}_{entry}_stale_pdst \
{signal_prefix}.rob_uop_{bank}_{entry}_is_fencei \
{signal_prefix}.rob_uop_{bank}_{entry}_uses_ldq \
{signal_prefix}.rob_uop_{bank}_{entry}_uses_stq \
{signal_prefix}.rob_uop_{bank}_{entry}_is_sys_pc2epc \
{signal_prefix}.rob_uop_{bank}_{entry}_flush_on_commit \
{signal_prefix}.rob_uop_{bank}_{entry}_ldst \
{signal_prefix}.rob_uop_{bank}_{entry}_ldst_val \
{signal_prefix}.rob_uop_{bank}_{entry}_dst_rtype \
{signal_prefix}.rob_uop_{bank}_{entry}_fp_val \
{signal_prefix}.rob_uop_{bank}_{entry}_debug_fsrc'''


base_group = '''gui_list_add_group -id ${{{wave_name}}} -after {{{parent_name}|{base_group_base_name}{idx:02d}}} {{{{{parent_name}|{base_group_base_name}{next_idx:02d}}}}}'''

# Function to generate the script for each slot
def generate_groups_and_signals(bank, entry):
    idx = (entry << 1) + bank
    if (bank==0):
        bank_string = ""
    else:
        bank_string = bank

    code = f'''# Rob entry {idx:02d}
set _session_group_{initial_session_group + idx} $_session_group_{parent_group}|
append _session_group_{initial_session_group + idx} {{idx {idx:02d}}}
gui_sg_create "$_session_group_{initial_session_group + idx}"
set {parent_name}|{base_group_base_name}{idx:02d} "$_session_group_{initial_session_group + idx}"

gui_sg_addsignal -group "$_session_group_{initial_session_group + idx}" {{ {base_signal.format(signal_prefix=signal_prefix, bank=bank_string, entry=entry, base_group=base_group, parent_name=parent_name, base_group_base_name=base_group_base_name)} }}
'''
    return code

# Generate and print the code for all slots
print('### Signals to groups')
for e in range(num_entries):
    for b in range(num_banks):
        idx = (e << 1) + b
        #print("b: {b}    e:{e}   idx:{idx:02d}".format(b=b, e=e, idx=idx))
        print(generate_groups_and_signals(bank=b, entry=e))

print('### Groups')

for e in range(num_entries):
    for b in range(num_banks):
        idx = (e << 1) + b
        print(base_group.format(wave_name=wave_name, parent_name=parent_name, base_group_base_name=base_group_base_name, idx=idx, next_idx=idx+1))

print('\nDone.')
