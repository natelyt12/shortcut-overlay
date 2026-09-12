#define UNICODE
#define _UNICODE

#include <windows.h>
#include <objidl.h>
#include <gdiplus.h>
#include <shellapi.h>
#include <string>
#include <vector>
#include <algorithm>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "gdiplus.lib")
#pragma comment(lib, "shell32.lib")

using namespace Gdiplus;

// -----------------------------------------------------------------------------
// Constants & IDs
// -----------------------------------------------------------------------------
#define WM_TRAYICON       (WM_USER + 1)
#define ID_TRAY_EXIT      1001
#define TIMER_HIDE_ID     101
#define HIDE_TIMEOUT_MS   3500
#define OVERLAY_HEIGHT    40
#define HORIZONTAL_PAD    22
#define TASKBAR_GAP       16

// -----------------------------------------------------------------------------
// Global State
// -----------------------------------------------------------------------------
HINSTANCE g_hInstance = NULL;
HWND g_hOverlayWnd = NULL;
HHOOK g_hKeyboardHook = NULL;
HANDLE g_hSingleInstanceMutex = NULL;
NOTIFYICONDATAW g_nid = { 0 };
ULONG_PTR g_gdiplusToken = 0;

std::wstring g_currentComboText = L"";
std::vector<std::wstring> g_activeModifiers;

// -----------------------------------------------------------------------------
// Helper: Rounded Rectangle Path for GDI+
// -----------------------------------------------------------------------------
void AddRoundedRect(GraphicsPath& path, RectF rect, float radius) {
    float diameter = radius * 2.0f;
    path.AddArc(rect.X, rect.Y, diameter, diameter, 180.0f, 90.0f);
    path.AddArc(rect.X + rect.Width - diameter, rect.Y, diameter, diameter, 270.0f, 90.0f);
    path.AddArc(rect.X + rect.Width - diameter, rect.Y + rect.Height - diameter, diameter, diameter, 0.0f, 90.0f);
    path.AddArc(rect.X, rect.Y + rect.Height - diameter, diameter, diameter, 90.0f, 90.0f);
    path.CloseFigure();
}

// -----------------------------------------------------------------------------
// Render Layered Glassmorphic Overlay
// -----------------------------------------------------------------------------
void RenderOverlay(const std::wstring& text) {
    if (!g_hOverlayWnd) return;

    if (text.empty()) {
        ShowWindow(g_hOverlayWnd, SW_HIDE);
        return;
    }

    HDC hdcScreen = GetDC(NULL);
    HDC hdcMem = CreateCompatibleDC(hdcScreen);

    // Measure text width using GDI+
    FontFamily fontFamily(L"Segoe UI");
    Gdiplus::Font font(&fontFamily, 12, FontStyleBold, UnitPoint);
    StringFormat format;
    format.SetAlignment(StringAlignmentCenter);
    format.SetLineAlignment(StringAlignmentCenter);

    Graphics measureGraphics(hdcMem);
    RectF layoutRect(0, 0, 1000.0f, (float)OVERLAY_HEIGHT);
    RectF boundRect;
    measureGraphics.MeasureString(text.c_str(), (int)text.length(), &font, layoutRect, &format, &boundRect);

    int textWidth = (int)boundRect.Width + 1;
    int winWidth = (std::max)(80, textWidth + HORIZONTAL_PAD * 2);
    int winHeight = OVERLAY_HEIGHT;

    // Create 32-bit ARGB DIB Section
    BITMAPINFO bmi = { 0 };
    bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bmi.bmiHeader.biWidth = winWidth;
    bmi.bmiHeader.biHeight = -winHeight; // Top-down
    bmi.bmiHeader.biPlanes = 1;
    bmi.bmiHeader.biBitCount = 32;
    bmi.bmiHeader.biCompression = BI_RGB;

    void* pvBits = NULL;
    HBITMAP hBitmap = CreateDIBSection(hdcScreen, &bmi, DIB_RGB_COLORS, &pvBits, NULL, 0);
    HBITMAP hOldBmp = (HBITMAP)SelectObject(hdcMem, hBitmap);

    // Paint using GDI+
    {
        Graphics g(hdcMem);
        g.SetSmoothingMode(SmoothingModeAntiAlias);
        g.SetTextRenderingHint(TextRenderingHintAntiAlias);

        // 1. Background pill: Black with 0.7 opacity (alpha 178)
        RectF rect(0.5f, 0.5f, (float)winWidth - 1.0f, (float)winHeight - 1.0f);
        GraphicsPath path;
        AddRoundedRect(path, rect, 10.0f);

        SolidBrush bgBrush(Color(178, 0, 0, 0));
        g.FillPath(&bgBrush, &path);

        // 2. Subtle glass highlight border
        Pen borderPen(Color(25, 255, 255, 255), 1.0f);
        g.DrawPath(&borderPen, &path);

        // 3. Text: Solid White
        SolidBrush textBrush(Color(255, 255, 255, 255));
        RectF textRect(0.0f, 0.0f, (float)winWidth, (float)winHeight);
        g.DrawString(text.c_str(), (int)text.length(), &font, textRect, &format, &textBrush);
    }

    // Reposition window horizontally centered right above the primary taskbar
    RECT workArea;
    SystemParametersInfoW(SPI_GETWORKAREA, 0, &workArea, 0);
    int posX = workArea.left + (workArea.right - workArea.left - winWidth) / 2;
    int posY = workArea.bottom - winHeight - TASKBAR_GAP;

    POINT ptSrc = { 0, 0 };
    POINT ptDst = { posX, posY };
    SIZE sizeWnd = { winWidth, winHeight };

    BLENDFUNCTION blend = { 0 };
    blend.BlendOp = AC_SRC_OVER;
    blend.SourceConstantAlpha = 255;
    blend.AlphaFormat = AC_SRC_ALPHA;

    UpdateLayeredWindow(g_hOverlayWnd, hdcScreen, &ptDst, &sizeWnd, hdcMem, &ptSrc, 0, &blend, ULW_ALPHA);
    ShowWindow(g_hOverlayWnd, SW_SHOWNOACTIVATE);

    // Reset inactivity timer
    SetTimer(g_hOverlayWnd, TIMER_HIDE_ID, HIDE_TIMEOUT_MS, NULL);

    // Cleanup
    SelectObject(hdcMem, hOldBmp);
    DeleteObject(hBitmap);
    DeleteDC(hdcMem);
    ReleaseDC(NULL, hdcScreen);
}

// -----------------------------------------------------------------------------
// Key Name Resolution & Filtering
// -----------------------------------------------------------------------------
bool IsModifierKey(DWORD vkCode, std::wstring& outName) {
    switch (vkCode) {
        case VK_CONTROL: case VK_LCONTROL: case VK_RCONTROL:
            outName = L"Ctrl"; return true;
        case VK_SHIFT: case VK_LSHIFT: case VK_RSHIFT:
            outName = L"Shift"; return true;
        case VK_MENU: case VK_LMENU: case VK_RMENU:
            outName = L"Alt"; return true;
        case VK_LWIN: case VK_RWIN:
            outName = L"Win"; return true;
        default:
            return false;
    }
}

std::wstring ResolveSpecialKey(DWORD vkCode) {
    if (vkCode >= VK_F1 && vkCode <= VK_F24) {
        return L"F" + std::to_wstring(vkCode - VK_F1 + 1);
    }
    switch (vkCode) {
        case VK_ESCAPE:    return L"Esc";
        case VK_TAB:       return L"Tab";
        case VK_CAPITAL:   return L"Caps";
        case VK_UP:        return L"↑";
        case VK_DOWN:      return L"↓";
        case VK_LEFT:      return L"←";
        case VK_RIGHT:     return L"→";
        case VK_DELETE:    return L"Del";
        case VK_INSERT:    return L"Ins";
        case VK_HOME:      return L"Home";
        case VK_END:       return L"End";
        case VK_PRIOR:     return L"PgUp";
        case VK_NEXT:      return L"PgDn";
        case VK_SNAPSHOT:  return L"PrtSc";
        case VK_NUMLOCK:   return L"NumLk";
        case VK_SCROLL:    return L"ScrLk";
        case VK_PAUSE:     return L"Pause";
        case VK_VOLUME_UP:   return L"Vol +";
        case VK_VOLUME_DOWN: return L"Vol -";
        case VK_VOLUME_MUTE: return L"Mute";
        case VK_MEDIA_PLAY_PAUSE: return L"Play";
        case VK_SPACE:     return L"Space";
        case VK_RETURN:    return L"Enter";
        case VK_BACK:      return L"Back";
        default:           return L"";
    }
}

std::wstring ResolveGeneralKey(DWORD vkCode) {
    if (vkCode >= 'A' && vkCode <= 'Z') {
        return std::wstring(1, (wchar_t)vkCode);
    }
    if (vkCode >= '0' && vkCode <= '9') {
        return std::wstring(1, (wchar_t)vkCode);
    }
    if (vkCode >= VK_NUMPAD0 && vkCode <= VK_NUMPAD9) {
        return L"Num " + std::to_wstring(vkCode - VK_NUMPAD0);
    }
    switch (vkCode) {
        case VK_OEM_1:      return L";";
        case VK_OEM_PLUS:   return L"+";
        case VK_OEM_COMMA:  return L",";
        case VK_OEM_MINUS:  return L"-";
        case VK_OEM_PERIOD: return L".";
        case VK_OEM_2:      return L"/";
        case VK_OEM_3:      return L"~";
        case VK_OEM_4:      return L"[";
        case VK_OEM_5:      return L"\\";
        case VK_OEM_6:      return L"]";
        case VK_OEM_7:      return L"'";
        default:            return L"";
    }
}

// -----------------------------------------------------------------------------
// Low-Level Keyboard Hook
// -----------------------------------------------------------------------------
LRESULT CALLBACK LowLevelKeyboardProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode == HC_ACTION) {
        KBDLLHOOKSTRUCT* kbd = (KBDLLHOOKSTRUCT*)lParam;
        DWORD vk = kbd->vkCode;

        std::wstring modName;
        bool isMod = IsModifierKey(vk, modName);

        if (wParam == WM_KEYDOWN || wParam == WM_SYSKEYDOWN) {
            if (isMod) {
                if (std::find(g_activeModifiers.begin(), g_activeModifiers.end(), modName) == g_activeModifiers.end()) {
                    g_activeModifiers.push_back(modName);
                }
                std::wstring combo = L"";
                for (size_t i = 0; i < g_activeModifiers.size(); ++i) {
                    if (i > 0) combo += L" + ";
                    combo += g_activeModifiers[i];
                }
                RenderOverlay(combo);
            } else {
                std::wstring specialKey = ResolveSpecialKey(vk);
                std::wstring generalKey = specialKey.empty() ? ResolveGeneralKey(vk) : specialKey;

                // Smart Filtering: ignore standalone normal typing
                if (g_activeModifiers.empty()) {
                    if (!specialKey.empty() && specialKey != L"Space" && specialKey != L"Enter" && specialKey != L"Back") {
                        RenderOverlay(specialKey);
                    }
                } else {
                    if (!generalKey.empty()) {
                        std::wstring combo = L"";
                        for (const auto& mod : g_activeModifiers) {
                            combo += mod + L" + ";
                        }
                        combo += generalKey;
                        RenderOverlay(combo);
                    }
                }
            }
        } else if (wParam == WM_KEYUP || wParam == WM_SYSKEYUP) {
            if (isMod) {
                auto it = std::find(g_activeModifiers.begin(), g_activeModifiers.end(), modName);
                if (it != g_activeModifiers.end()) {
                    g_activeModifiers.erase(it);
                }
            }
        }
    }
    return CallNextHookEx(g_hKeyboardHook, nCode, wParam, lParam);
}

// -----------------------------------------------------------------------------
// Window Procedure
// -----------------------------------------------------------------------------
LRESULT CALLBACK OverlayWndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
        case WM_TIMER:
            if (wParam == TIMER_HIDE_ID) {
                KillTimer(hwnd, TIMER_HIDE_ID);
                ShowWindow(hwnd, SW_HIDE);
                g_activeModifiers.clear();
            }
            return 0;

        case WM_TRAYICON:
            if (lParam == WM_RBUTTONUP) {
                POINT pt;
                GetCursorPos(&pt);
                HMENU hMenu = CreatePopupMenu();
                InsertMenuW(hMenu, 0, MF_BYPOSITION | MF_STRING, ID_TRAY_EXIT, L"Thoát");
                SetForegroundWindow(hwnd);
                TrackPopupMenu(hMenu, TPM_RIGHTBUTTON, pt.x, pt.y, 0, hwnd, NULL);
                DestroyMenu(hMenu);
            }
            return 0;

        case WM_COMMAND:
            if (LOWORD(wParam) == ID_TRAY_EXIT) {
                DestroyWindow(hwnd);
            }
            return 0;

        case WM_DESTROY:
            Shell_NotifyIconW(NIM_DELETE, &g_nid);
            PostQuitMessage(0);
            return 0;
    }
    return DefWindowProcW(hwnd, msg, wParam, lParam);
}

// -----------------------------------------------------------------------------
// Entry Point
// -----------------------------------------------------------------------------
int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE, LPSTR, int) {
    // 1. Single Instance Check
    g_hSingleInstanceMutex = CreateMutexW(NULL, FALSE, L"Global\\ShortcutOverlay_SingleInstance_Mutex");
    if (GetLastError() == ERROR_ALREADY_EXISTS) {
        if (g_hSingleInstanceMutex) CloseHandle(g_hSingleInstanceMutex);
        return 0;
    }

    g_hInstance = hInstance;

    // 2. Initialize GDI+
    GdiplusStartupInput gdiplusStartupInput;
    GdiplusStartup(&g_gdiplusToken, &gdiplusStartupInput, NULL);

    // 3. Register Window Class
    WNDCLASSEXW wc = { 0 };
    wc.cbSize = sizeof(WNDCLASSEXW);
    wc.lpfnWndProc = OverlayWndProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = L"ShortcutOverlayWindowClass";
    RegisterClassExW(&wc);

    // 4. Create Layered, Click-through Window
    g_hOverlayWnd = CreateWindowExW(
        WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_TOPMOST,
        wc.lpszClassName,
        L"Shortcut Overlay",
        WS_POPUP,
        0, 0, 100, OVERLAY_HEIGHT,
        NULL, NULL, hInstance, NULL
    );

    // 5. Setup System Tray Icon
    HICON hAppIcon = LoadIconW(hInstance, L"APP_ICON");
    if (!hAppIcon) hAppIcon = LoadIconW(NULL, (LPCWSTR)IDI_APPLICATION);

    g_nid.cbSize = sizeof(NOTIFYICONDATAW);
    g_nid.hWnd = g_hOverlayWnd;
    g_nid.uID = 1;
    g_nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP | NIF_INFO;
    g_nid.uCallbackMessage = WM_TRAYICON;
    g_nid.hIcon = hAppIcon;
    wcscpy_s(g_nid.szTip, L"Shortcut Overlay");
    wcscpy_s(g_nid.szInfoTitle, L"Shortcut Overlay");
    wcscpy_s(g_nid.szInfo, L"Ứng dụng đã khởi chạy và đang chạy nền.\nChuột phải vào biểu tượng ở khay hệ thống để thoát.");
    g_nid.dwInfoFlags = NIIF_INFO;
    Shell_NotifyIconW(NIM_ADD, &g_nid);

    // 6. Hook Global Keyboard
    g_hKeyboardHook = SetWindowsHookExW(WH_KEYBOARD_LL, LowLevelKeyboardProc, hInstance, 0);

    // 7. Message Loop
    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    // Cleanup
    if (g_hKeyboardHook) UnhookWindowsHookEx(g_hKeyboardHook);
    GdiplusShutdown(g_gdiplusToken);
    if (g_hSingleInstanceMutex) CloseHandle(g_hSingleInstanceMutex);

    return 0;
}

