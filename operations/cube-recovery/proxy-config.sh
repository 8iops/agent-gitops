# Bound workers to this Pod's CPU/memory allocation. Keep credentials out of argv.
umask 077
awk '
BEGIN {
  token = ENVIRON["CUBE_PROXY_ADMIN_TOKEN"]
  if (token !~ /^[a-f0-9]+$/ || length(token) != 64) exit 1
}
/^worker_processes / { print "worker_processes 2;"; next }
{
  gsub(/set \$cube_admin_token "";/, "set $cube_admin_token \"" token "\";")
  print
}' /usr/local/openresty/nginx/conf/nginx.conf > /usr/local/openresty/nginx/conf/nginx.conf.safe
mv /usr/local/openresty/nginx/conf/nginx.conf.safe /usr/local/openresty/nginx/conf/nginx.conf
