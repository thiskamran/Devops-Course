const express = require('express');
const os = require('os');
const { exec } = require('child_process');

const app = express();
const port = 8080;

function getIpAddress() {
    const interfaces = os.networkInterfaces();
    for (const name of Object.keys(interfaces)) {
        for (const iface of interfaces[name]) {
            if ('IPv4' !== iface.family || iface.internal !== false) {
                continue;
            }
            return iface.address;
        }
    }
    return '0.0.0.0';
}

function getProcesses() {
    return new Promise((resolve, reject) => {
        exec('ps -e -o comm=', (error, stdout) => {
            if (error) {
                reject(error);
            }
            resolve(stdout.split('\n').filter(Boolean));
        });
    });
}

function getDiskSpace() {
    return new Promise((resolve, reject) => {
        exec('df -h /', (error, stdout) => {
            if (error) {
                reject(error);
            }
            resolve(stdout.split('\n')[1].split(/\s+/).slice(1, 4).join(', '));
        });
    });
}

function getUptime() {
    return os.uptime();
}

app.get('/', async (req, res) => {
    try {
        const [processes, diskSpace] = await Promise.all([getProcesses(), getDiskSpace()]);
        res.json({
            "Service2": {
                "IP": getIpAddress(),
                "Processes": processes,
                "Disk Space": diskSpace,
                "Uptime": getUptime()
            }
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/stop', (req, res) => {
    console.log('Received stop request for service2');
    res.json({ message: 'Stopping service2...' });
    // Force kill the process
    process.kill(process.pid, 'SIGTERM');
});

// Add SIGTERM handler
process.on('SIGTERM', () => {
    console.log('SIGTERM received, shutting down...');
    process.exit(0);
});

// Add SIGINT handler as well for completeness
process.on('SIGINT', () => {
    console.log('SIGINT received, shutting down...');
    process.exit(0);
});

app.listen(port, () => {
    console.log(`Service2 running on port ${port}`);
});
