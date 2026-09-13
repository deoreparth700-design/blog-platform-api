require("dotenv").config();

const fs = require("fs");
const path = require("path");
const pool = require("../src/config/db");

async function initDb() {
  try {
    const schemaPath = path.join(__dirname, "../src/db/schema.sql");
    const schema = fs.readFileSync(schemaPath, "utf8");

    await pool.query(schema);
    console.log("Database schema initialized successfully.");
  } catch (error) {
    console.error("Failed to initialize database schema:", error.message);
    process.exitCode = 1;
  } finally {
    await pool.end();
  }
}

initDb();
