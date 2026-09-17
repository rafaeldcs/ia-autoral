using Microsoft.Data.Sqlite;
using System.Security.Cryptography;

enum PasswordCheck { Accepted, Denied, NotConfigured, Locked }

sealed class PublicationPasswordStore {
 const int Iterations=600000;
 readonly string connectionString;
 readonly object gate=new();
 public PublicationPasswordStore(string path) {
  connectionString=new SqliteConnectionStringBuilder{DataSource=path,Pooling=false}.ToString();
  using var db=Open();using var command=db.CreateCommand();
  command.CommandText="CREATE TABLE IF NOT EXISTS publication_password (id INTEGER PRIMARY KEY CHECK(id=1), salt BLOB NOT NULL, hash BLOB NOT NULL, iterations INTEGER NOT NULL, created_at INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS password_attempts (device TEXT PRIMARY KEY, failures INTEGER NOT NULL, locked_until INTEGER NOT NULL);";
  command.ExecuteNonQuery();
 }
 SqliteConnection Open(){var db=new SqliteConnection(connectionString);db.Open();return db;}
 public bool Configured {get{lock(gate){using var db=Open();using var command=db.CreateCommand();command.CommandText="SELECT COUNT(*) FROM publication_password";return (long)command.ExecuteScalar()!>0;}}}
 public bool SetOnce(string password) {
  if(password.Length<12||password.Length>256||string.IsNullOrWhiteSpace(password))throw new InvalidDataException("Use uma senha de 12 a 256 caracteres.");
  lock(gate){
   using var db=Open();using var command=db.CreateCommand();
   var salt=RandomNumberGenerator.GetBytes(32);
   var hash=Rfc2898DeriveBytes.Pbkdf2(password,salt,Iterations,HashAlgorithmName.SHA256,32);
   command.CommandText="INSERT OR IGNORE INTO publication_password(id,salt,hash,iterations,created_at) VALUES(1,$salt,$hash,$iterations,$now)";
   command.Parameters.AddWithValue("$salt",salt);command.Parameters.AddWithValue("$hash",hash);command.Parameters.AddWithValue("$iterations",Iterations);command.Parameters.AddWithValue("$now",DateTimeOffset.UtcNow.ToUnixTimeSeconds());
   return command.ExecuteNonQuery()==1;
  }
 }
 public PasswordCheck Verify(string device,string password) {
  lock(gate){
   using var db=Open();long now=DateTimeOffset.UtcNow.ToUnixTimeSeconds();
   using var query=db.CreateCommand();query.CommandText="SELECT MAX(locked_until) FROM password_attempts WHERE device=$device OR device='*'";query.Parameters.AddWithValue("$device",device);
   var locked=query.ExecuteScalar();if(locked is long until&&until>now)return PasswordCheck.Locked;
   using var credential=db.CreateCommand();credential.CommandText="SELECT salt,hash,iterations FROM publication_password WHERE id=1";
   using var reader=credential.ExecuteReader();if(!reader.Read())return PasswordCheck.NotConfigured;
   var salt=(byte[])reader[0];var expected=(byte[])reader[1];int iterations=reader.GetInt32(2);reader.Close();
   if(iterations!=Iterations||salt.Length!=32||expected.Length!=32)throw new InvalidDataException("Cadastro inválido.");
   bool valid=password.Length>=12&&password.Length<=256&&CryptographicOperations.FixedTimeEquals(expected,Rfc2898DeriveBytes.Pbkdf2(password,salt,iterations,HashAlgorithmName.SHA256,32));
   if(valid){using var reset=db.CreateCommand();reset.CommandText="DELETE FROM password_attempts WHERE device=$device";reset.Parameters.AddWithValue("$device",device);reset.ExecuteNonQuery();return PasswordCheck.Accepted;}
   using var transaction=db.BeginTransaction();
   foreach(var bucket in new[]{device,"*"}){
    using var attempt=db.CreateCommand();attempt.Transaction=transaction;
    attempt.CommandText="INSERT INTO password_attempts(device,failures,locked_until) VALUES($device,1,0) ON CONFLICT(device) DO UPDATE SET failures=CASE WHEN locked_until>0 AND locked_until<=$now THEN 1 ELSE failures+1 END, locked_until=CASE WHEN (CASE WHEN locked_until>0 AND locked_until<=$now THEN 1 ELSE failures+1 END)>=$limit THEN $now+60 ELSE 0 END";
    attempt.Parameters.AddWithValue("$device",bucket);attempt.Parameters.AddWithValue("$now",now);attempt.Parameters.AddWithValue("$limit",bucket=="*"?20:5);attempt.ExecuteNonQuery();
   }
   transaction.Commit();return PasswordCheck.Denied;
  }
 }
}
