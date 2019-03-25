#!/bin/bash
if [ -n "$(command -v apt-get)" ]; then
    sudo apt -y update
    sudo apt install -y java-1.8.0-openjdk-devel.x86_64
elif [ -n "$(command -v yum)" ]; then
    sudo yum -y update
    sudo yum -y install java-1.8.0-openjdk-devel.x86_64
fi

wget http://www-eu.apache.org/dist/tomcat/tomcat-9/v9.0.17/bin/apache-tomcat-9.0.17.tar.gz -P /tmp
sudo mkdir -p /opt/tomcat
tar xf /tmp/apache-tomcat-9*.tar.gz -C /opt/tomcat
ln -s /opt/tomcat/apache-tomcat-9* /opt/tomcat/latest
sudo chmod +x /opt/tomcat/latest/bin/
sudo chmod 777 -R /opt/tomcat/latest

if [ "$(pidof /sbin/init && echo "sysvinit" || echo "other")" != "other" ]; then
    sudo touch /etc/init.d/tomcat
    sudo chmod 777 /etc/init.d/tomcat
    sudo echo -e "#!/bin/sh
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
  APP_ID=\$(ps -ef | grep \$PID | grep -v grep | grep -v \"\$PID start\" || echo \"other\")
  if [[ \$APP_ID != \"other\" ]]; then
    echo 'Service already running' >&2
    return 1
  fi
  echo 'Starting service' >&2
  \"\$START\"
  echo 'Service started' >&2
}
stop() {
  APP_ID=\$(ps -ef | grep \$PID | grep -v grep | grep -v \"\$PID stop\" || echo \"other\")
  if [[ \$APP_ID == \"other\" ]]; then
    echo 'Service not running' >&2
    return 1
  fi
  echo 'Stopping service' >&2
  \"\$STOP\"
  echo 'Service stopped' >&2
}
case \"\$1\" in
  start)
    start
    ;;
  stop)
    stop
    ;;
  restart)
    stop
    sleep 10
    start
    ;;
  *)
    echo \"Usage: \$0 {start|stop|restart}\"
esac" >> /etc/init.d/tomcat
    sudo chmod +x /etc/init.d/tomcat
    service tomcat start
    sudo chmod 777 -R /opt/tomcat/latest
    chkconfig --list
    sudo chkconfig --add tomcat
elif [ "$(pidof systemd && echo "systemd" || echo "other")" != "other" ]; then
    sudo echo -e "Description=Tomcat 9 servlet container ?'
After=network.target
[Service]
Type=forking
User=tomcat
Group=tomcat
Environment=\"JAVA_HOME=/usr/lib/jvm/default-java\"
Environment=\"JAVA_OPTS=-Djava.security.egd=file:///dev/urandom -Djava.awt.headless=true\"
Environment=\"CATALINA_BASE=/opt/tomcat/latest\"
Environment=\"CATALINA_HOME=/opt/tomcat/latest\"
Environment=\"CATALINA_PID=/opt/tomcat/latest/temp/tomcat.pid\"
Environment=\"CATALINA_OPTS=-Xms512M -Xmx1024M -server -XX:+UseParallelGC\"
ExecStart=/opt/tomcat/latest/bin/startup.sh
ExecStop=/opt/tomcat/latest/bin/shutdown.sh
[Install]
WantedBy=multi-user.target" >> /etc/systemd/system/tomcat.service
    sudo systemctl daemon-reload
    sudo systemctl start tomcat
    sudo systemctl enable tomcat
fi