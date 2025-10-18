#!/bin/bash
# MongoDB ReplicaSet Initialization Script

echo "Waiting for MongoDB instances to be ready..."
sleep 10

mongosh --host mongodb-primary:27017 -u "${MONGO_INITDB_ROOT_USERNAME}" -p "${MONGO_INITDB_ROOT_PASSWORD}" --eval "
try {
  var status = rs.status();
  print('ReplicaSet already initialized');
} catch (e) {
  print('Initializing ReplicaSet...');
  rs.initiate({
    _id: 'rs0',
    members: [
      { _id: 0, host: 'mongodb-primary:27017', priority: 2 },
      { _id: 1, host: 'mongodb-secondary1:27017', priority: 1 },
      { _id: 2, host: 'mongodb-secondary2:27017', priority: 1 }
    ]
  });
  
  print('Waiting for ReplicaSet to stabilize...');
  sleep(5000);
  
  print('Creating application user...');
  db = db.getSiblingDB('admin');
  db.createUser({
    user: '${MONGODB_USER}',
    pwd: '${MONGODB_PASSWORD}',
    roles: [
      { role: 'readWrite', db: '${MONGODB_DATABASE}' },
      { role: 'dbAdmin', db: '${MONGODB_DATABASE}' }
    ]
  });
  
  print('ReplicaSet initialization completed!');
}
"
