// MONGO_INITDB_DATABASE 환경변수로 이미 해당 DB 컨텍스트에서 실행됨
// getSiblingDB 호출 불필요 (하드코딩 제거)

db.createCollection('draws');
db.createCollection('predictions');

db.draws.createIndex({ drwNo: 1 }, { unique: true });
db.draws.createIndex({ drwNoDate: -1 });

db.predictions.createIndex({ created_at: -1 });
db.predictions.createIndex({ model_type: 1 });
db.predictions.createIndex({ model_version: 1 });
