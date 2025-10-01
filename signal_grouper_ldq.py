# Define the range of banks
num_banks = 1  # Adjust this to generate more slots (up to 19 slots as per your original request)

# Define the range of banks
num_entries = 16  # Adjust this to generate more slots (up to 19 slots as per your original request)

# Parent group
parent_group = 320
parent_name = "LSU|LDQ"

# Group
initial_session_group = parent_group + 1
base_group_base_name = "ldq entry "

# Wave name
wave_name = "Wave.1"

# Add this string in a new line to add a divider 
# divider = f'''gui_sg_addsignal -group "$_session_group_{initial_session_group + idx}" {{ Divider }} -divider'''

# String for adding new group after the previous one
base_group = '''gui_list_add_group -id ${{{wave_name}}} -after {{{parent_name}|{base_group_base_name}{idx:02d}}} {{{{{parent_name}|{base_group_base_name}{next_idx:02d}}}}}'''

signal_prefix = 'TestDriver.testHarness.chiptop.system.tile_prci_domain.tile_reset_domain.boom_tile.lsu.ldq'

# Base template for generating the code
base_signal = ['''{signal_prefix}_{entry}_valid \
{signal_prefix}_{entry}_bits_executed \
{signal_prefix}_{entry}_bits_succeeded \
{signal_prefix}_{entry}_bits_failure \
{signal_prefix}_{entry}_bits_order_fail \
{signal_prefix}_{entry}_bits_observed \
{signal_prefix}_{entry}_bits_st_dep_mask[15:0] \
{signal_prefix}_{entry}_bits_youngest_stq_idx[3:0] \
{signal_prefix}_{entry}_bits_forward_std_val \
{signal_prefix}_{entry}_bits_forward_stq_idx[3:0]''',

'''{signal_prefix}_{entry}_bits_uop_uopc[6:0] \
{signal_prefix}_{entry}_bits_uop_br_mask[11:0] \
{signal_prefix}_{entry}_bits_uop_rob_idx[5:0] \
{signal_prefix}_{entry}_bits_uop_ldq_idx[3:0] \
{signal_prefix}_{entry}_bits_uop_stq_idx[3:0] \
{signal_prefix}_{entry}_bits_uop_pdst[6:0] \
{signal_prefix}_{entry}_bits_uop_mem_cmd[4:0] \
{signal_prefix}_{entry}_bits_uop_mem_size[1:0] \
{signal_prefix}_{entry}_bits_uop_mem_signed \
{signal_prefix}_{entry}_bits_uop_is_fence \
{signal_prefix}_{entry}_bits_uop_is_amo \
{signal_prefix}_{entry}_bits_uop_uses_ldq \
{signal_prefix}_{entry}_bits_uop_uses_stq \
{signal_prefix}_{entry}_bits_uop_dst_rtype[1:0] \
{signal_prefix}_{entry}_bits_uop_fp_val \
{signal_prefix}_{entry}_bits_uop_taint \
{signal_prefix}_{entry}_bits_uop_yrot[5:0]''',

'''{signal_prefix}_{entry}_bits_addr_valid \
{signal_prefix}_{entry}_bits_addr_bits[39:0] \
{signal_prefix}_{entry}_bits_addr_is_virtual \
{signal_prefix}_{entry}_bits_addr_is_uncacheable''']


# Function to generate the script for each slot
def generate_groups_and_signals(idx):
    code = f'''# {base_group_base_name} {idx:02d}
set _session_group_{initial_session_group + idx} $_session_group_{parent_group}|
append _session_group_{initial_session_group + idx} {{{base_group_base_name}{idx:02d}}}
gui_sg_create "$_session_group_{initial_session_group + idx}"
set {{{parent_name}|{base_group_base_name}{idx:02d}}} "$_session_group_{initial_session_group + idx}"
'''

    for bs in base_signal:
        code += f'''gui_sg_addsignal -group "$_session_group_{initial_session_group + idx}" {{ {bs.format(signal_prefix=signal_prefix, entry=idx)} }}\n'''
        if (bs != base_signal[-1]):
            code +=f'''gui_sg_addsignal -group "$_session_group_{initial_session_group + idx}" {{ Divider }} -divider\n'''

    return code

# Generate and print the code for all slots
print('### Signals to groups')
for e in range(num_entries):
    #print("b: {b}    e:{e}   idx:{idx:02d}".format(b=b, e=e, idx=idx))
    print(generate_groups_and_signals(e))

print('\n### Groups')
# First group goes after parent
print("gui_list_add_group -id ${{{wave_name}}} -after {{{parent_name}}} {{{{{parent_name}|{base_group_base_name}{idx:02d}}}}}".format(wave_name=wave_name, parent_name=parent_name, base_group_base_name=base_group_base_name, idx=0))
for e in range(num_entries-1):
    # Rest of groups goes after the previous group
    print(base_group.format(wave_name=wave_name, parent_name=parent_name, base_group_base_name=base_group_base_name, idx=e, next_idx=e+1))

print('\n#Done.')
