#!/usr/bin/env node
/*
  Make Superadmin Script (production-safe)
  - Promotes an existing user to superadmin, or creates a minimal user record if not present
  - Requires MongoDB connection string (MONGODB_URI) with write access to the users collection
  - Usage (PowerShell):
      $env:MONGODB_URI="mongodb+srv://user:pass@cluster/db?retryWrites=true&w=majority";
      node backend/scripts/make-superadmin.js --email "you@example.com" --yes
    Or:
      node backend/scripts/make-superadmin.js --email "you@example.com" --mongo "mongodb://..." --yes
*/

const mongoose = require('mongoose');
const path = require('path');
try { require('dotenv').config({ path: path.resolve(process.cwd(), '.env') }); } catch (_) {}

function parseArgs() {
  const args = process.argv.slice(2);
  const out = { yes: false };
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--email' && args[i + 1]) { out.email = args[++i]; continue; }
    if (a === '--mongo' && args[i + 1]) { out.mongo = args[++i]; continue; }
    if (a === '--name' && args[i + 1]) { out.name = args[++i]; continue; }
    if (a === '--tenant' && args[i + 1]) { out.tenantId = args[++i]; continue; }
    if (a === '--yes' || a === '-y') { out.yes = true; continue; }
    if (a === '--help' || a === '-h') { out.help = true; continue; }
  }
  return out;
}

async function main() {
  const args = parseArgs();
  if (args.help || !args.email) {
    console.log('Usage: node backend/scripts/make-superadmin.js --email "you@example.com" [--mongo "mongodb-uri"] [--name "Full Name"] [--tenant "tenantId"] [--yes]');
    process.exit(args.help ? 0 : 1);
  }

  const mongoUri = args.mongo || process.env.MONGODB_URI;
  if (!mongoUri) {
    console.error('Error: MONGODB_URI not provided. Use --mongo or set MONGODB_URI env var.');
    process.exit(1);
  }

  const inProd = (process.env.NODE_ENV === 'production');
  if (inProd && !args.yes) {
    console.error('Refusing to run in production without --yes flag. Re-run with --yes to confirm.');
    process.exit(1);
  }

  console.log(`Connecting to MongoDB...`);
  await mongoose.connect(mongoUri, {
    serverSelectionTimeoutMS: 15000,
  });

  // Minimal schema bound to existing collection
  const userSchema = new mongoose.Schema({
    email: { type: String, required: true, unique: true },
    role: { type: String },
    isActive: { type: Boolean },
    name: { type: String },
    tenantId: { type: String },
  }, { strict: false, collection: 'users' });

  const User = mongoose.model('User_SA_Admin', userSchema);

  const update = {
    role: 'superadmin',
    isActive: true,
  };
  if (args.name) update.name = args.name;
  if (args.tenantId) update.tenantId = args.tenantId; // usually superadmin should NOT have tenantId

  console.log(`Promoting/creating superadmin for email: ${args.email}`);

  // Try update existing
  let user = await User.findOneAndUpdate(
    { email: args.email },
    { $set: update },
    { new: true }
  );

  if (!user) {
    // Create minimal user (no credentials yet; WebAuthn registration needed later)
    user = await User.create({
      email: args.email,
      name: args.name || 'Super Admin',
      role: 'superadmin',
      isActive: true,
      // Do NOT set credentials here; user must register WebAuthn in the UI
    });
  }

  console.log(JSON.stringify({ id: user._id?.toString?.() || String(user._id), email: user.email, role: user.role, isActive: user.isActive }, null, 2));
  await mongoose.disconnect();
}

main().catch(async (err) => {
  console.error('Failed:', err?.message || err);
  try { await mongoose.disconnect(); } catch (_) {}
  process.exit(1);
});
