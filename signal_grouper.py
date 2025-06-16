# Define the range of slots you want to generate
num_slots = 20  # Adjust this to generate more slots (up to 19 slots as per your original request)

# Define the initial session group ID
initial_session_group = 30  # You can modify this to start at any group ID

signal_prefix = 'TestDriver.testHarness.chiptop.system.tile_prci_domain.tile_reset_domain.boom_tile.core.int_issue_unit.issue_slots'

# Base template for generating the code
base_signal_1 = '''{signal_prefix}_{slot}_grant \
{signal_prefix}_{slot}_in_uop_valid \
{signal_prefix}_{slot}_request \
{signal_prefix}_{slot}_uop_br_mask \
{signal_prefix}_{slot}_uop_br_tag \
{signal_prefix}_{slot}_uop_bypassable \
{signal_prefix}_{slot}_uop_dst_rtype \
{signal_prefix}_{slot}_uop_edge_inst \
{signal_prefix}_{slot}_uop_fp_val \
{signal_prefix}_{slot}_uop_ftq_idx \
{signal_prefix}_{slot}_uop_fu_code \
{signal_prefix}_{slot}_uop_imm_packed \
{signal_prefix}_{slot}_uop_is_amo \
{signal_prefix}_{slot}_uop_is_br \
{signal_prefix}_{slot}_uop_is_jal \
{signal_prefix}_{slot}_uop_is_jalr \
{signal_prefix}_{slot}_uop_is_rvc \
{signal_prefix}_{slot}_uop_is_sfb \
{signal_prefix}_{slot}_uop_iw_p1_poisoned \
{signal_prefix}_{slot}_uop_iw_p2_poisoned \
{signal_prefix}_{slot}_uop_ldq_idx \
{signal_prefix}_{slot}_uop_ldst_val \
{signal_prefix}_{slot}_uop_lrs1_rtype \
{signal_prefix}_{slot}_uop_lrs2_rtype \
{signal_prefix}_{slot}_uop_mem_cmd \
{signal_prefix}_{slot}_uop_pc_lob \
{signal_prefix}_{slot}_uop_pdst \
{signal_prefix}_{slot}_uop_prs1 \
{signal_prefix}_{slot}_uop_prs2 \
{signal_prefix}_{slot}_uop_rob_idx'''

base_signal_2 = '''{signal_prefix}_{slot}_uop_taint \
{signal_prefix}_{slot}_uop_taken \
{signal_prefix}_{slot}_uop_uopc \
{signal_prefix}_{slot}_uop_uses_stq \
{signal_prefix}_{slot}_uop_yrot \
{signal_prefix}_{slot}_valid \
{signal_prefix}_{slot}_will_be_valid'''

base_group = '''gui_list_add_group -id ${{Wave.1}} -after {{Issue Unit|Slot {slot}}} {{{{Issue Unit|Slot {next_slot}}}}}'''

# Function to generate the script for each slot
def generate_slot_code(slot_number, session_group_start):
    code = f'''# Issue slot {slot_number}
set _session_group_{session_group_start + slot_number} $_session_group_{session_group_start - 1}|
append _session_group_{session_group_start + slot_number} {{Slot {slot_number}}}
gui_sg_create "$_session_group_{session_group_start + slot_number}"
set {{Issue Unit|Slot {slot_number}}} "$_session_group_{session_group_start + slot_number}"

gui_sg_addsignal -group "$_session_group_{session_group_start + slot_number}" {{ {base_signal_1.format(signal_prefix=signal_prefix, slot=slot_number)} }}
gui_sg_addsignal -group "$_session_group_{session_group_start + slot_number}" {{ {base_signal_2.format(signal_prefix=signal_prefix, slot=slot_number)} }}
'''
    return code

# Generate and print the code for all slots
print('### Signals to groups')
for slot in range(num_slots):
    print(generate_slot_code(slot, initial_session_group))

print('### Groups')

for slot in range(num_slots):
    print(base_group.format(slot=slot, next_slot=slot+1))

print('\nDone.')
