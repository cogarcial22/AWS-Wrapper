#!/bin/sh
#
# tomcat          Start/Stop the cron clock daemon.
#
# chkconfig: 2345 90 60
# description: tomcat is a standard UNIX program that runs user-specified \
#              programs at periodic scheduled times. vixie cron adds a \
#              number of features to the basic UNIX cron, including better \
#              security and more powerful configuration options.
START=/opt/tomcat/latest/bin/startup.sh
STOP=/opt/tomcat/latest/bin/shutdown.sh
PID=tomcat
export JRE_HOME=/usr/lib/jvm/java-1.8.0
export JAVA_HOME=/usr/lib/jvm/java-1.8.0
start() {
  if [ -n "$(ps -ef | grep \$PID | grep -v grep)" ]; then
    echo 'Service already running' >&2
    return 1
  fi
  echo 'Starting service' >&2
  "$START"
  echo 'Service started' >&2
}
stop() {
  if [ -z "$(ps -ef | grep \$PID | grep -v grep)" ]; then
    echo 'Service not running' >&2
    return 1
  fi
  echo 'Stopping service' >&2
  \"\$STOP\"
  echo 'Service stopped' >&2
}
case "$1" in
  start)
    start
    ;;
  stop)
    stop
    ;;
  restart)
    stop
    start
    ;;
  *)
    echo "Usage: $0 {start|stop|restart}"
esac
