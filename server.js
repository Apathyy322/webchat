const express = require('express');
const app = express();
const http = require('http').createServer(app);
const io = require('socket.io')(http, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});
const cors = require('cors');
const { Sequelize, DataTypes } = require('sequelize');
require('dotenv').config();

// Configure logging
const winston = require('winston');
const logger = winston.createLogger({
    level: 'info',
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
    ),
    transports: [
        new winston.transports.Console()
    ]
});

// Database configuration
const sequelize = new Sequelize(process.env.DATABASE_URL || 'postgres://postgres:password@localhost:5432/chatdb', {
    dialect: 'postgres',
    dialectOptions: {
        ssl: process.env.DATABASE_URL ? {
            require: true,
            rejectUnauthorized: false
        } : false
    },
    logging: msg => logger.debug(msg)
});

// User model
const User = sequelize.define('User', {
    username: {
        type: DataTypes.STRING(80),
        unique: true,
        allowNull: false
    }
});

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Routes
app.get('/', (req, res) => {
    res.sendFile(__dirname + '/public/index.html');
});

app.post('/register', async (req, res) => {
    try {
        const { username } = req.body;
        
        if (!username) {
            logger.warn('Registration attempted with empty username');
            return res.status(400).send('Username is required');
        }

        const existingUser = await User.findOne({ where: { username } });
        if (existingUser) {
            logger.info(`Registration attempted with existing username: ${username}`);
            return res.status(400).send('Username already exists');
        }

        await User.create({ username });
        logger.info(`New user registered: ${username}`);
        res.status(200).send('User registered successfully');
    } catch (error) {
        logger.error('Error during registration:', error);
        res.status(500).send('Registration failed');
    }
});

// Socket.IO events
io.on('connection', (socket) => {
    logger.info(`Client connected: ${socket.id}`);

    socket.on('chat message', (data) => {
        try {
            const { username, message } = data;
            if (username && message) {
                logger.info(`Received message from ${username}`);
                io.emit('chat message', { username, message });
            } else {
                logger.warn('Received incomplete message data');
            }
        } catch (error) {
            logger.error('Error handling message:', error);
        }
    });

    socket.on('disconnect', () => {
        logger.info(`Client disconnected: ${socket.id}`);
    });
});

// Error handling
app.use((err, req, res, next) => {
    logger.error('Internal server error:', err);
    res.status(500).send('Internal Server Error');
});

// Database initialization and server start
const PORT = process.env.PORT || 5000;

async function startServer() {
    try {
        await sequelize.sync();
        logger.info('Database synchronized successfully');
        
        http.listen(PORT, () => {
            logger.info(`Server running on port ${PORT}`);
        });
    } catch (error) {
        logger.error('Failed to start server:', error);
        process.exit(1);
    }
}

startServer();

module.exports = app; // For testing purposes
