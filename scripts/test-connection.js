require("dotenv").config();

const pool = require("../src/config/db");

async function testConnection() {
  try {
    const result = await pool.query("SELECT NOW()");
    console.log("Connected to PostgreSQL.");
    console.log("Server time:", result.rows[0].now);
  } catch (error) {
    console.error("Failed to connect to PostgreSQL:", error.message);
    process.exitCode = 1;
  } finally {
    await pool.end();
  }
}

testConnection();
