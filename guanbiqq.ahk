#Requires AutoHotkey v2.0

#Esc:: {
    hwnd := WinExist("ahk_class Chrome_WidgetWin_1")
    if hwnd {
        ControlSend("{Esc}", , hwnd)
    }
}