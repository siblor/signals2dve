# Generate view in a new toplevel
set TopLevel1 [gui_create_window -type TopLevel]
set Wave1 [gui_create_window -type Wave -parent $TopLevel1]

# Open new window
gui_show_window -window $Wave1 -show_state maximized

# Save
gui_save_session -file empty_wave_session.tcl -post

# For old versions (<2019) this requires manual confirmation. Just click OK when prompt to exit
# exit -force
exit