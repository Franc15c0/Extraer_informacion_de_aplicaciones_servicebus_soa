import array as arr
import os
from com.bea.wli.config import Ref
from com.bea.wli.config.env import EnvValueQuery
from com.bea.wli.config.env import QualifiedEnvValue
from com.bea.wli.config.resource import DependencyQuery
from com.bea.wli.sb.management.configuration import ALSBConfigurationMBean
from com.bea.wli.sb.management.configuration import SessionManagementMBean
from com.bea.wli.sb.management.query import BusinessServiceQuery
from com.bea.wli.sb.management.query import ProxyServiceQuery
from com.bea.wli.sb.util import EnvValueTypes
from com.ziclix.python.sql import zxJDBC
import java.util
from java.util import Collection
from java.util import Collections
from java.util import HashSet
from java.util import Hashtable
import javax.management
from javax.management import ObjectName
import javax.management.remote
from javax.management.remote import JMXConnectorFactory
from javax.management.remote import JMXServiceURL
import javax.naming
from javax.naming import Context
import weblogic.management.mbeanservers.domainruntime
from weblogic.management.mbeanservers.domainruntime import DomainRuntimeServiceMBean
import datetime


#Funcion que genera conexion a base de datos y regresa cursor para manejo de db
def makeDatabaseConnection(url, username, password, driver):
    conn = zxJDBC.connect(url, username, password, driver)
    cursor = conn.cursor(1)
    return cursor, conn
	
def realizaInsertArray(arreglo, cursor):
    for line in arreglo:
        cursor.execute(line)

def displayAllProjectsAndServices(ambiente, configMBean):
	relAllProject = []
	refs = configMBean.getRefs(Ref.DOMAIN)
	refsList = ArrayList()
	refsList.addAll(refs)
	for ref in refs:
		if (ref.isProjectRef()):
			insert = "insert into izzi_OSBPROJECTS (OSBPROJECTNAME, AMBIENTE) values ('" + ref.getFullName() + "','"+ambiente+"')"
			relAllProject.append(insert)

	for ref in refsList:
		if ref.getTypeId() == "ProxyService" or ref.getTypeId() == "BusinessService":
			if ref.getTypeId() == "ProxyService":
			 isPS = "1"
			else:
			 isPS = "0"
			insert = "INSERT INTO izzi_SERVICES (SERVICENAME, SERVICEFULLPATH, OSBPROJECTNAME, ISPS, AMBIENTE) values ('" + ref.getLocalName() + "', '" + ref.getFullName() + "', '" + ref.getProjectName() + "', '" + isPS + "','"+ambiente+"')"
			relAllProject.append(insert)
			update = "UPDATE izzi_SERVICES set SERVICENAME = '" + ref.getLocalName() + "', OSBPROJECTNAME='" + ref.getProjectName() + "', ISPS = '" + isPS + "' where SERVICEFULLPATH = '" + ref.getFullName() + "'"
			relAllProject.append(update)

	return relAllProject



def getAllServiceURIs(ambiente, configMBean):

    relAllServicesURI = [];

    evquery = EnvValueQuery(None, Collections.singleton(EnvValueTypes.SERVICE_URI), None, False, None, False)

    founds = configMBean.findEnvValues(evquery)

    for value in founds:

        update = "UPDATE izzi_SERVICES set SERVICE_URI = '" + value.getValue() + "' where SERVICEFULLPATH ='" + value.getOwner().getFullName() + "'"

        relAllServicesURI.append(update)

    return relAllServicesURI



def getAllProxyServices(ambiente, configMBean):

    query = ProxyServiceQuery()

    refs = configMBean.getRefs(query)

    relAllProxys = [];

    for ref in refs:

        uriObject = configMBean.getEnvValue(ref, EnvValueTypes.SERVICE_URI, None)

        if uriObject == None:

            uri = "NULL"

        else:

            uri = uriObject

            update = "UPDATE izzi_SERVICES set SERVICE_URI ='" + uri + "', TYPE = '" + lookupType(uri) + "', ISPS = 1 where SERVICEFULLPATH = '" + ref.getFullName() + "'"

            relAllProxys.append(update)

    return relAllProxys



def getAllBusinessServices(ambiente, configMBean):

    relAllBS = [];

    query = BusinessServiceQuery()

    refs = configMBean.getRefs(query)

    for ref in refs:

        uri = getBusinessServiceURI(ref, configMBean)

        update = "UPDATE izzi_SERVICES set SERVICE_URI ='" + uri + "', TYPE = '" + lookupType(uri) + "', ISPS = 0 where SERVICEFULLPATH = '" + ref.getFullName() + "'"

        relAllBS.append(update)

    return relAllBS



def getDependentServices(ambiente, configMBean):
    psQuery = ProxyServiceQuery()
    myPSSet = configMBean.getRefs(psQuery)
    relDepServices = [];
    for myPS in myPSSet:
		depQuery = DependencyQuery(Collections.singleton(myPS), False)
		refs = configMBean.getRefs(depQuery)
		for ref in refs:
			if (ref.getTypeId() == "BusinessService" or ref.getTypeId() == "ProxyService"):
				update = "INSERT INTO izzi_service_dependencies (SERVICE,DEPENDENTSERVICE, AMBIENTE) values ('" + myPS.getFullName() + "','" + ref.getFullName() + "','"+ambiente+"')"
				print update
				relDepServices.append(update)

    return relDepServices



def getBusinessServiceURI(ref, configMBean):

    envValueTypesToSearch = HashSet()

    envValueTypesToSearch.add(EnvValueTypes.SERVICE_URI);

    evquery = EnvValueQuery(None, envValueTypesToSearch, Collections.singleton(ref), False, None, False)

    founds = configMBean.findEnvValues(evquery);

    uri = ""

    for qev in founds:

        if (qev.getEnvValueType() == EnvValueTypes.SERVICE_URI):

            uri = qev.getValue()

    return uri;

                

def lookupType(uri):

    result = "NONE"

    if (uri == None):

        result = "LOCAL"

    elif uri.startswith("/"):

        result = "HTTP"

    elif (uri.startswith("jca://eis/DB/")):

        result = "DBADAPTER"

    elif (uri.startswith("flow:")):

        result = "SPLITJOIN"

    elif (uri.startswith("http://")):

        result = "HTTPBS"

    elif (uri.startswith("jca://eis/FileAdapter")):

        result = "HAFILEADAPTER"

    elif (uri.startswith("jca://eis/Ftp/")):

        result = "FTPADAPTER"

    elif (uri.startswith("jms:")):

        result = "JMS"

    return result;

def ejecutaOSB(userAdmin, passAdmin, portAdmin, hostnameAdmin, ambiente):
 now = datetime.datetime.now()
 sessionName = "SesionScriptOSB_"+str(now.day)+"_"+str(now.month)+"_"+str(now.year)+"_"+ambiente
 print "t3", hostnameAdmin, portAdmin, "/jndi/" + DomainRuntimeServiceMBean.MBEANSERVER_JNDI_NAME
 serviceURL = JMXServiceURL("t3", hostnameAdmin, int(portAdmin), "/jndi/" + DomainRuntimeServiceMBean.MBEANSERVER_JNDI_NAME)
 h = Hashtable()
 h.put(Context.SECURITY_PRINCIPAL, userAdmin)
 h.put(Context.SECURITY_CREDENTIALS, passAdmin)
 h.put(JMXConnectorFactory.PROTOCOL_PROVIDER_PACKAGES, "weblogic.management.remote")
 conn = JMXConnectorFactory.connect(serviceURL, h)

 arregloAllProject = []
 arregloAllProxy = []
 arregloAllBS = []
 arregloAllServicesURI = []
 arregloAllDependentS = []
 
 mbconn = conn.getMBeanServerConnection()
 sm = JMX.newMBeanProxy(mbconn, ObjectName.getInstance(SessionManagementMBean.OBJECT_NAME), SessionManagementMBean)
 sm.createSession(sessionName)
 configMBean = JMX.newMBeanProxy(mbconn, ObjectName.getInstance("com.bea:Name=" + ALSBConfigurationMBean.NAME + "." + sessionName + ",Type=" + ALSBConfigurationMBean.TYPE), ALSBConfigurationMBean)
 print "##############################"
 print "###Se genera conexion a OSB###"
 print "##############################"
 arregloAllProject=displayAllProjectsAndServices(ambiente, configMBean)
 arregloAllProxy=getAllProxyServices(ambiente, configMBean)
 arregloAllBS=getAllBusinessServices(ambiente, configMBean)                               
 arregloAllServicesURI=getAllServiceURIs(ambiente, configMBean)
 arregloAllDependentS=getDependentServices(ambiente, configMBean)
 sm.discardSession(sessionName)
 conn.close()
	
 return arregloAllProject, arregloAllProxy, arregloAllBS, arregloAllServicesURI, arregloAllDependentS


#Se reciben parametros de conexion a db de insert
if (len(sys.argv) > 10):

 #Se obtienen datos de conexion de parametros
 host = sys.argv[1].strip()
 port = sys.argv[2].strip()
 SID = sys.argv[3].strip()
 username = sys.argv[4].strip()
 password = sys.argv[5].strip()
 ambiente = sys.argv[6].strip()
 userAdmin = sys.argv[7].strip()
 passAdmin = sys.argv[8].strip()
 portAdmin = sys.argv[9].strip()
 hostnameAdmin = sys.argv[10].strip()
 #Datos de conexión a db
 jdbc_url="jdbc:oracle:thin:@"+host+":"+port+":"+SID
 #username="XML_USER"
 #password="Qazedctgb0103"
 driver="oracle.jdbc.xa.client.OracleXADataSource"
 print "------------------------------------------"
 print "Entrada"
 print "ambiente: " + ambiente
 print "userAdmin: " + userAdmin
 print "passAdmin: " + passAdmin
 print "portAdmin: " + portAdmin
 print "hostnameAdmin: " + hostnameAdmin
 print "jdbc_url: " + jdbc_url
 print "username: " + username
 print "password: " + password
 print "driver: " + driver 
 
 #Ejecuta OSB 
 arregloAllProject, arregloAllProxy, arregloAllBS, arregloAllServicesURI, arregloAllDependentS = ejecutaOSB(userAdmin, passAdmin, portAdmin, hostnameAdmin,ambiente)



 cursor, connDB=makeDatabaseConnection(jdbc_url, username, password, driver)
 print "#######################################"
 print "###Se genera conexion a db de insert###"
 print "#######################################"
 
 print arregloAllProject
 realizaInsertArray(arregloAllProject, cursor)
 realizaInsertArray(arregloAllProxy, cursor)
 realizaInsertArray(arregloAllBS, cursor)
 realizaInsertArray(arregloAllServicesURI, cursor)
 realizaInsertArray(arregloAllDependentS, cursor)
 connDB.commit()
 print "Termina ejecucion"
else:
 print "No se encontraron todos los parametros necesarios"


