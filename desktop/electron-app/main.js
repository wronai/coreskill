const { app, BrowserWindow, shell } = require('electron');

const URL = process.env.CORESKILL_URL || 'http://localhost:3000';

function createWindow() {
    const win = new BrowserWindow({
        width: 1024,
        height: 768,
        title: 'CoreSkill — AI Assistant',
        icon: undefined,
        autoHideMenuBar: true,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
        },
    });

    win.loadURL(URL);

    // Open external links in system browser
    win.webContents.setWindowOpenHandler(({ url }) => {
        if (url.startsWith('http') && !url.includes('localhost')) {
            shell.openExternal(url);
            return { action: 'deny' };
        }
        return { action: 'allow' };
    });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
