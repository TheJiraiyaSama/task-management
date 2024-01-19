from array import *
from datetime import date
from datetime import datetime
from distutils.log import debug
from importlib.abc import ResourceReader
import matplotlib.pyplot
import json
import sqlite3
from flask import Flask,render_template,redirect,url_for,request,session,after_this_request,flash
app=Flask(__name__)
app.secret_key="super secret key"
app.config['SESSION TYPE']='filesystem'
loginsuccess=0
dbName='Kanban.db'

class Summary:
    def __init__(self, LIST, No_of_Tasks, completed_before_due, completed_after_due, pending_passed_due, pending_yet_due, inprogress):
        self.LIST = LIST
        self.No_of_Tasks = No_of_Tasks
        self.completed_before_due = completed_before_due
        self.completed_after_due = completed_after_due
        self.pending_passed_due = pending_passed_due
        self.pending_yet_due = pending_yet_due
        self.inprogress = inprogress

@app.route('/showcards')
def showcards():
    cList=[]
    cname=request.args.get('cname')    
    cList=showcard(cname)   
    #lst=movlist()
    return render_template('showcards.html',lst=cList)

@app.route('/',methods=['GET','POST'])
def first_page():
    r=[]
    msg=""
    userSQL=""
    print("first_page")
    if(request.method=='POST'):
        username=request.form["username"]
        password=request.form["password"]
        userSQL="select username,password from Users where username='"+username+"'and password='"+password+"'"
        print(userSQL)
        r=getQueryResults(userSQL)
        for i in r:
            if(username==i[0] and password==i[1]):
                session['loggedin']=True
                session['username']=username
                loginsuccess=1
                return redirect(url_for('about'))
            else: 
                flash("Invalid username or password")
                loginsuccess=0
        #conn.commit()
    return render_template('first_page.html')

@app.route('/about')
def about():
    lst=[]
    #if (loginsuccess == 0):
    #    return render_template('first_page.html')
    lst=displaylist()
    return render_template('about.html',list=lst)   

@app.route('/signup')
def signup():
    loginsuccess=0
    return render_template('signup.html')

@app.route('/signup',methods=['GET','POST'])
def create():
    loginsuccess=0
    if(request.method=='POST'):
       username=request.form["username"]
       password=request.form["password"]
       email=request.form["email"]
       signqry="INSERT INTO Users VALUES('"+username+"', '"+password+"','"+email+"')"
       conn=sqlite3.connect(dbName)
       c=conn.cursor()
       c.execute(signqry)
       conn.commit()
       c.close()
       conn.close()
       flash("succesfully created")
       return render_template('first_page.html')
    else:
        flash("not created")
        return render_template('first_page.html')

@app.route('/addlist')
def addlist():
    resList=[]
    resList = displaylist()
    return render_template('addlist.html', resultList=resList)

@app.route('/addlist',methods=['GET','POST'])
def make_list():
    msg=""
    rList=[]  
    if(request.method=='POST'):
        listname=request.form['listname'] 
        description=request.form['description']
        if not listname:
            msg="List Cannot be NULL"
        else:
            conn=sqlite3.connect(dbName)
            c=conn.cursor()
            c.execute("insert into Lists (listname, description, status) values('"+listname+"','"+description+"', 'Open')")
            conn.commit()
            c.close()
            conn.close()
            msg="List Created, add another?"       
        rList=displaylist()          
        return render_template('addlist.html',msg=msg, resultList=rList)
    else:
        msg="List not Created"   
    return render_template('about.html',msg=msg)

def displaylist():
    # This to display All the Lists
    return getQueryResults("select * from Lists")

def displaycards():
    return getQueryResults("select * from Cards")

@app.route('/addcard')
def addcard():
    lname=request.args.get('addlname')
    return render_template("addcard.html",listname=lname)

@app.route('/addcard',methods=['GET','POST'])
def make_card():
    msg=""
    listid=[]
    lname=request.args.get('addlname')    
    if(request.method=='POST'):
        conn=sqlite3.connect(dbName)
        c=conn.cursor()
        c.execute("select listid from Lists where listname = '"+lname+"'")
        listid = c.fetchone()
        for row in listid:
            if row==None:
                msg="List can't be empty! Card not Added"
            else:
                cardname=request.form['cardname'] 
                description=request.form["description"]
                duedate=request.form["duedate"]
                c.execute("insert into Cards (listid, cardname, description, duedate, status) values('"+str(row)+"','"+cardname+"','"+description+"','"+duedate+"', 'Pending')")
                conn.commit()
                c.close()
                conn.close()
                msg="Card Added to the List, add another?"
            return render_template('addcard.html',msg=msg,listname=lname)        
    else:
        msg="Card not Added"
    return render_template('about.html',msg=msg)

@app.route('/summary')
def summary():
    summary=[]
    crdsummary=[]
    labels=[]
    values=[]
    crdsummary = displaysummary()
    summary=graphsummary(crdsummary)
    summaryval=summary[-1]
    labels = ["Completed", "Completed-Delay", "Ready-Start", "Start-Delay", "In-Progress"]
    values=[summaryval.completed_before_due, summaryval.completed_after_due, summaryval.pending_yet_due, summaryval.pending_passed_due, summaryval.inprogress]
    #print(labels)
    #print(values)
    return render_template('summary.html', resultsummary=crdsummary, label=labels, value=values)

@app.route('/summary',methods=['GET','POST'])
def summary_create():
    summary=[]
    crdsummary=[]
    labels=[]
    values=[]
    crdsummary = displaysummary()
    summary=graphsummary(crdsummary)
    summaryval=summary[-1]
    labels = {"Completed Before Due", "Completed After Due", "Pending Yet Start", "Pending Past Due", "In Progress"}
    values={summaryval.completed_before_due, summaryval.completed_after_due, summaryval.pending_yet_due, summaryval.pending_passed_due, summaryval.inprogress }
    #print(labels)
    #print(values)
    return render_template('summary.html', resultsummary=crdsummary, label=labels, value=values)

def graphsummary(crdsummary):
    summary=[]
    dupelabels=[]
    labels=[]
    values=[]
    LISTS=[]
    Total_Tasks=[]
    completed_before_due=[]
    completed_after_due=[]
    pending_passed_due=[]
    pending_yet_due=[]
    today=date.today()
    #print("TODAY : ", today)
    crdsummary = displaysummary()
    dupelabels = [row[2] for row in crdsummary]
    labels = [*set(dupelabels)]
    LISTS = [*set([row[1] for row in crdsummary])]
    for lab in labels:
        k=0
        for dlab in dupelabels:
            if (lab == dlab):
                k=k+1    
        values.append(k)
        cc=0
        ccbd=0
        ccad=0
        pcyd=0
        pcpd=0
        inp=0
        for lst in LISTS:
            for lab in labels:
                for rows in crdsummary:
                    if (rows[1] == lst):
                        if (rows[2] == lab):
                            cc = cc+1
                            rowdate=datetime.strptime(rows[4], '%Y-%m-%d').date()
                            if ((rowdate <= today) and (rows[5] == "Complete")):	
                                ccbd = ccbd+1
                            elif (rows[5] == "Complete"):
                                ccad = ccad+1
                            if ((rowdate <= today) and (rows[5] == "Pending")):	
                                pcyd = pcyd+1
                            elif (rows[5] == "Pending"):
                                pcpd = pcpd+1
                            if (rows[5] == "Progress"):
                                inp = inp+1    
                            summary.append(Summary(lst, cc, ccbd, ccad, pcyd, pcpd, inp))
    return summary

@app.route('/modcard')
def modcard():
    lst=[]
    crd=[]
    cname=request.args.get('modcname')    
    lst=cardlists()
    crd=getcard(cname)
    print(crd)
    print(lst)
    return render_template('modcard.html',cardist=crd,lists=lst)

@app.route('/modcard',methods=['GET','POST'])
def modify_card():
    lst=[]
    crd=[]
    crdid=[]
    lstid=[]
    qry=""
    cname=request.args.get('modcname') 
    cstatus=request.form.get('status')   
    clist=request.form.get('changecrd')
    carddesc=request.form.get('crddesc')
    #crddue=request.form.get('crddue')    
    conn=sqlite3.connect(dbName)
    c=conn.cursor()
    cl=conn.cursor()    
    cc=conn.cursor()    
    c.execute("select cardid from Cards where cardname='"+str(cname)+"'")
    cl.execute("select listid from Lists where listname='"+str(clist)+"'")
    crdid=c.fetchone()
    lstid=cl.fetchone()
    qry="update Cards set "
    desc=-1   
    if clist:
        desc=0
        qry=qry+"listid="+str(lstid[0])        
    if cstatus:
        if desc==0:
            qry=qry+", status='"+cstatus+"'"
        else:
            qry=qry+" status='"+cstatus+"'"
            desc=0  
    if carddesc:
        if desc==0:
            qry=qry+", description='"+carddesc+"' where cardid="+str(crdid[0])
        else:
            qry=qry+" description='"+carddesc+"' where cardid="+str(crdid[0])
        desc=1
    if desc==0:
            qry=qry+" where cardid="+str(crdid[0])     
    cc.execute(qry)
    conn.commit()
    c.close()
    cc.close()    
    conn.close()
    crd=getcard(cname)
    lst=cardlists()
    return render_template('modcard.html',cardist=crd,lists=lst)

def displaysummary():
    # This to display All the Lists
    resultsummary=[]
    conn=sqlite3.connect(dbName)
    c=conn.cursor()    
    c.execute("select crd.cardid, lst.listname, crd.cardname, crd.description, crd.duedate, crd.status from Cards crd, Lists lst where crd.listid=lst.listid")
    resultsummary.extend(c.fetchall())
    c.close()
    conn.close()
    return resultsummary

@app.route('/dellist',methods=['GET','POST'])
def dellist():
    msg=""
    listid=[]
    lname=request.args.get('dellname')    
    if(request.method=='GET'):
        if not lname:
            msg="List Cannot be NULL"
        else:
            conn=sqlite3.connect(dbName)
            cl=conn.cursor()
            cc=conn.cursor()            
            cc.execute("delete from Cards where listid= (select listid from Lists where listname='"+lname+"')")
            cl.execute("delete from Lists where listname = '"+lname+"'") 
            conn.commit()
            cc.close()
            cl.close()            
            conn.close()
            msg="List Deleted"       
        rList=displaylist()          
        return render_template('addlist.html',msg=msg, resultList=rList)
    else:
        msg="List not Deleted"
    return render_template('about.html',msg=msg)

@app.route('/delcard',methods=['GET','POST'])
def delcard():
    cid=request.args.get('delcid')  
    conn=sqlite3.connect(dbName)
    c=conn.cursor()
    c.execute("delete from Cards where cardid='"+cid+"'")
    conn.commit()
    c.close()
    crdsummary = displaysummary()
    return render_template('summary.html', resultsummary=crdsummary)

@app.route('/modlist')
def modlist():
    rList=[]
    lname=request.args.get('modlname')    
    rList=getlist(lname)   
    #lst=movlist()
    return render_template('modlist.html', resultList=rList)

@app.route('/modlist',methods=['GET','POST'])
def modify_list():
    msg=""
    qry=""
    rList=[]
    lname=request.args.get('modlname')    
    description=request.form.get('description')
    status=request.form.get('status')
    if (status == "Closed"):
        if ( checkcardstatus(lname) > 0):
            status="Open"

    qry="update Lists set "
    desc=1    
    if description:
        desc=0
        qry=qry+"description='"+description+"'"
        if status:
            qry=qry+", status='"+status+"' where listname='"+lname+"'"
        else:
            qry=qry+" where listname='"+lname+"'"       
    elif status:
        qry=qry+"status='"+status+"' where listname='"+lname+"'"
        desc=0
    else:
        desc=1
        qry=""
    if(request.method=='POST'):
        if not lname:
            msg="List Cannot be NULL"
        elif desc!=1:
            conn=sqlite3.connect(dbName)
            c=conn.cursor()
            c.execute(qry)
            conn.commit()
            c.close()
            conn.close()
            msg="List Updated"        
            rList=getlist(lname)   
            return render_template('modlist.html',msg=msg, resultList=rList)
        else:
            msg="Nothing to Update"            
    else:
        msg="List not Deleted"
    rList=displaylist()     
    return render_template('addlist.html',msg=msg, resultList=rList)

def checkcardstatus(lname):
    openyn=0
    conn=sqlite3.connect(dbName)
    c=conn.cursor()    
    c.execute("select count(*) from Cards where status!='Complete' and listid=(select listid from Lists where listname='"+lname+"')")
    openyn=c.fetchone()
    c.close()
    conn.close()
    return openyn[0]

def getlist(lstname):
    return getQueryResults("select * from Lists where listname='"+lstname+"'")
    
def getcard(cardname):
    # This to display one Lists record by listname
    resultCard=[]
    conn=sqlite3.connect(dbName)
    c=conn.cursor()    
    c.execute("select crd.cardname, crd.description, crd.status, lst.listname from Cards crd, Lists lst where crd.listid=lst.listid and crd.cardname='"+cardname+"'")
    resultCard.extend(c.fetchall())
    c.close()
    conn.close()
    return resultCard
    
def showcard(listid):
    resultlst=[]
    conn=sqlite3.connect(dbName)
    c=conn.cursor()
    c.execute("select crd.cardname,crd.description,crd.status,lst.listname from Cards crd,Lists lst where crd.listid='"+listid+"' and lst.listid='"+listid+"'")
    resultlst.extend(c.fetchall())
    c.close()
    conn.commit()
    conn.close()
    return resultlst

def updatecard(cname):
    sql="select crd.cardid, lst.listname, crd.cardname, crd.description, crd.status from Cards crd, Lists lst where crd.listid = lst.listid and crd.cardname='"+cname+"'"
    return getQueryResults(sql)

def cardlists():
    cardata=[]
    lstdata=[]
    cardata=getQueryResults("select listname from Lists")
    print(cardata)
    lstdata=[i[0] for i in cardata]
    return lstdata

def DBConnection(dbName):
    return sqlite3.connect(dbName)

def InsertData(iQuery):
    return

def getQueryResults(query):
    resultSet=[]
    conn=DBConnection(dbName)
    c=conn.cursor()
    c.execute(query)
    resultSet.extend(c.fetchall())
    DBClose(conn)
    return resultSet

def DBClose(conn):
    conn.close()

if __name__=='__main__':
    app.run(debug=True)