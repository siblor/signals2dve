# Generate Wave view in a new toplevel and save the session
set newWave [gui_create_window -type Wave -parent [gui_create_window -type TopLevel]]
gui_show_window -window $newWave -show_state maximized
# For old versions (<2019) this requires manual confirmation. Just click OK when prompt to exit
# exit -force
exit


