// Runs on first start: creates the assignment database and its readWrite user
db = db.getSiblingDB("movies_db");
db.createUser({
  user: "g110",
  pwd: "g110pass",
  roles: [{ role: "readWrite", db: "movies_db" }],
});
