"""Windows process-tree loopback. No virtual cable or system-wide fallback."""
import ctypes as ct
from ctypes import wintypes as wt
import sys
import threading
import os

import comtypes
from comtypes import COMMETHOD, GUID, HRESULT, IUnknown
import numpy as np
import psutil
from i18n import UserMessageError


def discord_processes():
    found = {}
    for proc in psutil.process_iter(['pid', 'ppid', 'name', 'create_time']):
        if (proc.info['name'] or '').lower() in {'discord.exe', 'discordptb.exe', 'discordcanary.exe'}:
            found[proc.pid] = proc.info
    return [p for p in found.values() if p['ppid'] not in found]


def application_processes(include_background=False):
    """Select visible apps and browser roots, not individual renderer children."""
    import win32gui
    import win32process
    visible = set()
    def visit(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            visible.add(win32process.GetWindowThreadProcessId(hwnd)[1])
    win32gui.EnumWindows(visit, None)
    rows = {}
    for process in psutil.process_iter(['pid', 'ppid', 'name', 'create_time', 'username']):
        info = process.info
        if info['name'] and info['create_time'] is not None:
            rows[info['pid']] = info
    return select_application_roots(rows, visible, os.getpid(), include_background,
                                    psutil.Process().username())


def select_application_roots(rows, visible, own_pid, include_background, username):
    known = {'discord.exe', 'discordptb.exe', 'discordcanary.exe', 'chrome.exe',
             'msedge.exe', 'firefox.exe', 'brave.exe', 'opera.exe'}
    excluded = {own_pid}
    # Exclude our parent process when a frozen executable or shell spawns a child.
    current = rows.get(own_pid)
    while current and current['ppid'] in rows and rows[current['ppid']]['name'].lower() == current['name'].lower():
        excluded.add(current['ppid'])
        current = rows[current['ppid']]
    selected = {}
    for pid, info in rows.items():
        if pid in excluded or info['name'].lower() == 'yukitranslator.exe':
            continue
        if pid not in visible and info['name'].lower() not in known:
            if not include_background or info.get('username') != username:
                continue
        root = info
        visited = {pid}
        while root['ppid'] in rows and root['ppid'] not in visited:
            parent = rows[root['ppid']]
            if parent['name'].lower() != root['name'].lower() or parent['create_time'] > root['create_time']:
                break
            visited.add(parent['pid'])
            root = parent
        if root['pid'] not in excluded:
            selected[root['pid']] = root
    return sorted(selected.values(), key=lambda p: (p['name'].lower() != 'discord.exe', p['name'].lower(), p['pid']))


class WaveFormat(ct.Structure):
    _pack_ = 1
    _fields_ = [('tag', wt.WORD), ('channels', wt.WORD), ('rate', wt.DWORD),
                ('bytes_per_second', wt.DWORD), ('alignment', wt.WORD),
                ('bits', wt.WORD), ('extra', wt.WORD)]


class Activation(ct.Structure):
    _fields_ = [('type', ct.c_int), ('pid', wt.DWORD), ('mode', ct.c_int)]


class Blob(ct.Structure):
    _fields_ = [('size', wt.ULONG), ('data', ct.c_void_p)]


class PropVariant(ct.Structure):
    _fields_ = [('vt', wt.WORD), ('reserved', wt.WORD * 3), ('blob', Blob)]


class AudioClient(IUnknown):
    _iid_ = GUID('{1CB9AD4C-DBFA-4c32-B178-C2F568A703B2}')
    _methods_ = [
        COMMETHOD([], HRESULT, 'Initialize', (['in'], ct.c_int, 'mode'), (['in'], wt.DWORD, 'flags'),
                  (['in'], ct.c_longlong, 'duration'), (['in'], ct.c_longlong, 'period'),
                  (['in'], ct.POINTER(WaveFormat), 'format'), (['in'], ct.c_void_p, 'session')),
        COMMETHOD([], HRESULT, 'GetBufferSize', (['out'], ct.POINTER(wt.UINT), 'frames')),
        COMMETHOD([], HRESULT, 'GetStreamLatency', (['out'], ct.POINTER(ct.c_longlong), 'latency')),
        COMMETHOD([], HRESULT, 'GetCurrentPadding', (['out'], ct.POINTER(wt.UINT), 'frames')),
        COMMETHOD([], HRESULT, 'IsFormatSupported', (['in'], ct.c_int, 'mode'),
                  (['in'], ct.c_void_p, 'format'), (['in'], ct.c_void_p, 'closest')),
        COMMETHOD([], HRESULT, 'GetMixFormat', (['out'], ct.POINTER(ct.c_void_p), 'format')),
        COMMETHOD([], HRESULT, 'GetDevicePeriod', (['out'], ct.POINTER(ct.c_longlong), 'default'),
                  (['out'], ct.POINTER(ct.c_longlong), 'minimum')),
        COMMETHOD([], HRESULT, 'Start'), COMMETHOD([], HRESULT, 'Stop'), COMMETHOD([], HRESULT, 'Reset'),
        COMMETHOD([], HRESULT, 'SetEventHandle', (['in'], wt.HANDLE, 'event')),
        COMMETHOD([], HRESULT, 'GetService', (['in'], ct.POINTER(GUID), 'iid'),
                  (['out'], ct.POINTER(ct.POINTER(IUnknown)), 'service')),
    ]


class CaptureClient(IUnknown):
    _iid_ = GUID('{C8ADBD64-E71E-48a0-A4DE-185C395CD317}')
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetBuffer', (['out'], ct.POINTER(ct.c_void_p), 'data'),
                  (['out'], ct.POINTER(wt.UINT), 'frames'), (['out'], ct.POINTER(wt.DWORD), 'flags'),
                  (['out'], ct.POINTER(ct.c_ulonglong), 'position'),
                  (['out'], ct.POINTER(ct.c_ulonglong), 'clock')),
        COMMETHOD([], HRESULT, 'ReleaseBuffer', (['in'], wt.UINT, 'frames')),
        COMMETHOD([], HRESULT, 'GetNextPacketSize', (['out'], ct.POINTER(wt.UINT), 'frames')),
    ]


class AsyncOperation(IUnknown):
    _iid_ = GUID('{72A22D78-CDE4-431D-B8CC-843A71199B6D}')
    _methods_ = [COMMETHOD([], HRESULT, 'GetActivateResult',
                          (['out'], ct.POINTER(HRESULT), 'result'),
                          (['out'], ct.POINTER(ct.POINTER(IUnknown)), 'client'))]


class CompletionHandler(IUnknown):
    _iid_ = GUID('{41D949AB-9862-444A-80F6-C261334DA5EB}')
    _methods_ = [COMMETHOD([], HRESULT, 'ActivateCompleted', (['in'], ct.POINTER(AsyncOperation), 'operation'))]


class AgileObject(IUnknown):
    _iid_ = GUID('{94EA2B94-E9CC-49E0-C0FF-EE64CA8F5B90}')
    _methods_ = []


class Completion(comtypes.COMObject):
    _com_interfaces_ = [CompletionHandler, AgileObject]

    def __init__(self):
        self.done = threading.Event()
        self.client = None
        self.error = None

    def ActivateCompleted(self, operation):
        try:
            result, unknown = operation.GetActivateResult()
            if result < 0:
                raise OSError(f'WASAPI activation: 0x{result & 0xffffffff:08X}')
            self.client = unknown.QueryInterface(AudioClient)
        except Exception as exc:
            self.error = exc
        finally:
            self.done.set()
        return 0


kernel = ct.WinDLL('kernel32', use_last_error=True)
kernel.CreateEventW.argtypes = [ct.c_void_p, wt.BOOL, wt.BOOL, wt.LPCWSTR]
kernel.CreateEventW.restype = wt.HANDLE
kernel.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
kernel.WaitForSingleObject.restype = wt.DWORD
kernel.CloseHandle.argtypes = [wt.HANDLE]


class ProcessCapture:
    rate = 48000

    def __init__(self, pid):
        self.pid = pid
        self.client = self.capture = self.operation = self.callback = self.event = None
        self.started = False

    def __enter__(self):
        if sys.getwindowsversion().build < 20348:
            raise UserMessageError('capture_windows')
        comtypes.CoInitializeEx(0)
        try:
            self.callback = Completion()
            params = Activation(1, self.pid, 0)  # include the selected process and its children
            prop = PropVariant(65, (wt.WORD * 3)(), Blob(ct.sizeof(params), ct.addressof(params)))
            activate = ct.OleDLL('Mmdevapi').ActivateAudioInterfaceAsync
            activate.argtypes = [wt.LPCWSTR, ct.POINTER(GUID), ct.POINTER(PropVariant),
                                 ct.POINTER(CompletionHandler), ct.POINTER(ct.POINTER(AsyncOperation))]
            activate.restype = HRESULT
            self.operation = ct.POINTER(AsyncOperation)()
            activate('VAD\\Process_Loopback', ct.byref(AudioClient._iid_), ct.byref(prop),
                     self.callback.QueryInterface(CompletionHandler), ct.byref(self.operation))
            if not self.callback.done.wait(10):
                raise UserMessageError('capture_timeout')
            if self.callback.error:
                raise self.callback.error
            self.client = self.callback.client
            fmt = WaveFormat(1, 2, self.rate, self.rate * 4, 4, 16, 0)
            self.client.Initialize(0, 0x80060000, 0, 0, ct.byref(fmt), None)
            self.capture = self.client.GetService(ct.byref(CaptureClient._iid_)).QueryInterface(CaptureClient)
            self.event = kernel.CreateEventW(None, False, False, None)
            if not self.event:
                raise ct.WinError(ct.get_last_error())
            self.client.SetEventHandle(self.event)
            self.client.Start()
            self.started = True
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def read(self):
        """Return copied mono float samples. A bounded wait keeps Stop responsive."""
        result = kernel.WaitForSingleObject(self.event, 20)
        if result == 0xffffffff:
            raise ct.WinError(ct.get_last_error())
        blocks = []
        while self.capture.GetNextPacketSize():
            data, frames, flags, _, _ = self.capture.GetBuffer()
            try:
                if flags & 2:
                    blocks.append(np.zeros(frames, dtype=np.float32))
                else:
                    raw = ct.string_at(data, frames * 4)
                    blocks.append(np.frombuffer(raw, dtype=np.int16).reshape(-1, 2).mean(axis=1).astype(np.float32) / 32768)
            finally:
                self.capture.ReleaseBuffer(frames)
        return np.concatenate(blocks) if blocks else np.empty(0, dtype=np.float32)

    def __exit__(self, *_):
        try:
            if self.started:
                self.client.Stop()
        finally:
            self.started = False
            self.capture = self.client = self.operation = None
            if self.callback:
                self.callback.client = None
            self.callback = None
            if self.event:
                kernel.CloseHandle(self.event)
                self.event = None
            comtypes.CoUninitialize()
