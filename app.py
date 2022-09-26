from flask import Flask, url_for, request, render_template, redirect
import paramiko, re, time
import sys

app = Flask(__name__)

# CONSTANTS
HOST = ''
USERNAME = ''
PASS = ''
REMOVE_FOLDERS = ['lixeira',]

auth_remote = {}

users = {
    "admin": "admin"
}

# This function get all folders inside the folder smb
def get_folders():
    # Connection with SSHClient
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USERNAME, password=PASS)
    # Run command 
    stdin, stdout, stderr = ssh.exec_command("ls /smb", get_pty = True)
    # Get results and decode to UTF-8
    result = stdout.read().decode("utf-8")
    # Split the results
    folders = result.split()
    # Remove specific folders from constant REMOVE_FOLDERS
    for folder in REMOVE_FOLDERS:
        folders.remove(folder)
    # Return folders
    return folders

def verify_ip():
    if request.remote_addr not in auth_remote:
        auth_remote[request.remote_addr] = False

# Show all folders
@app.route('/folders')
def folders():
    # Test is logged
    verify_ip()
    if auth_remote[request.remote_addr] == False:
        return redirect(url_for('login'))
    # Get all folders
    folders = get_folders()
    # Create an array to put informations from folders and size
    foldersWithSize = []
    # Loop to manipulate each folder
    for folder in folders:   
        # Connect to SSHClient
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOST, username=USERNAME, password=PASS)
        # Execute command
        stdin, stdout, stderr = ssh.exec_command(f'ls -sh /smb/{folder}', get_pty = True)
        # Decode result
        result = stdout.read().decode("utf-8")
        # Create an array with 'folder - size'
        foldersWithSize.append(f'{folder} - {result[6:10]}')
    print(foldersWithSize)
    # Return result
    return result

@app.route('/template')
def template():
    # Test is logged
    verify_ip()
    if auth_remote[request.remote_addr] == False:
        return redirect(url_for('login'))
    return render_template('userGroups.html')

# Route to show users access
@app.route('/userGroups/<user>', methods=['GET', 'POST'])
def userGroups(user):
    # Test is logged
    verify_ip()
    if auth_remote[request.remote_addr] == False:
        return redirect(url_for('login'))
    # Get all folders because the folders have the same name of the access
    folders = get_folders()
    folders.sort()
    # If POST
    if request.method == 'POST':
        # Get all checked items
        new_groups = request.form.getlist('checkbox')
        # Connection with SSHClient
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOST, username=USERNAME, password=PASS)
        # Run command
        stdin, stdout, stderr = ssh.exec_command(f"sudo groups {user}", get_pty = True)
        # Add password for sudo command
        stdin.write(PASS+'\n')
        stdin.flush()
        # Decode the result
        result = stdout.read().decode("utf-8")
        # If doesn't exist user
        if ('No such user' in result):
            print('Não existe usuário')
        # If exist user
        else:
            # Split user's group getting only the groups
            groups = result.split()[8:]
            # Diff getting groups which was removed
            groups_removed = set(groups).difference(set(new_groups))
            # Diff getting groups which was addded
            groups_added = set(new_groups).difference(set(groups))
            # if groups_added has at least one new access
            if(len(groups_added) > 0):
                # Loop to get each access to add
                for folder in groups_added:
                    command = f'sudo adduser {user} {folder}'
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(HOST, username=USERNAME, password=PASS)
                    stdin, stdout, stderr = ssh.exec_command(command, get_pty = True)
                    stdin.write(PASS+'\n')
                    stdin.flush()
            # if groups_removed has at least one access to be removed
            if(len(groups_removed) > 0):
                # Loop to get each access to remove
                for folder in groups_removed:
                    # command = f'sudo gpasswd -d {user} '+','.join(groups_removed)
                    command = f'sudo gpasswd -d {user} {folder}'
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(HOST, username=USERNAME, password=PASS)
                    stdin, stdout, stderr = ssh.exec_command(command, get_pty = True)
                    stdin.write(PASS+'\n')
                    stdin.flush()
        # Redirect
        return redirect(f'/userGroups/{user}')
    # If not POST
    else:
        # Connection with SSHClient
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOST, username=USERNAME, password=PASS)
        # Run command
        stdin, stdout, stderr = ssh.exec_command(f"sudo groups {user}", get_pty = True)
        # Add password to sudo command
        stdin.write(PASS+'\n')
        stdin.flush()
        # Decode the result
        result = stdout.read().decode("utf-8")
        # If user doesn't exist
        if ('No such user' in result):
            # groups = result.split()[8:]
            return render_template('userGroups.html', folders=folders, username=user, new=True)
        # If user exists
        else:
            # Get user's access
            groups = result.split()[8:]
            return render_template('userGroups.html', folders=folders, groups=groups, username=user)
        # return html
        return html

@app.route('/')
def index():
    # Test is logged
    verify_ip()
    if auth_remote[request.remote_addr] == False:
        return redirect(url_for('login'))
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USERNAME, password=PASS)
    command = 'sudo pdbedit -L'
    stdin, stdout, stderr = ssh.exec_command(command, get_pty = True)
    stdin.write(PASS+'\n')
    stdin.flush()
    # Decode the result
    result = stdout.read().decode("utf-8")
    # Get all users excluding information from beggining
    users  = result.split()[5:]
    # Get all users without unnecessary information
    users = [user.split(':')[0] for user in users]
    # Get total of users
    total_users = len(users)

    #Ver Pastas
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USERNAME, password=PASS)
    command = 'ls /smb'
    stdin, stdout, stderr = ssh.exec_command(command, get_pty = True)
    stdin.flush()
    # Decode the result
    result = stdout.read().decode("utf-8")
    # print(result)
    # Get all users excluding information from beggining
    folders  = result.split()
    # print(folders)
    for folder in REMOVE_FOLDERS:
        folders.remove(folder)
    # Get total of folders
    total_folders = len(folders)

    return render_template('index.html', total_users=total_users, total_folders=total_folders)

# Bring user's list
@app.route('/usersList')
def usersList():
    # Test is logged
    verify_ip()
    if auth_remote[request.remote_addr] == False:
        return redirect(url_for('login'))
    # Connect to SSHClient
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USERNAME, password=PASS)
    # Run the command
    command = 'sudo pdbedit -L'
    stdin, stdout, stderr = ssh.exec_command(command, get_pty = True)
    # Write the password
    stdin.write(PASS+'\n')
    stdin.flush()
    # Decode the result
    result = stdout.read().decode("utf-8")
    # Get all users excluding information from beggining
    users  = result.split()[5:]
    # Get all users without unnecessary information
    users = [user.split(':')[0] for user in users]
    # Sort users
    users.sort()
    # Get total of users
    total = len(users)
    return render_template('usersList.html', users=users, total=total)

@app.route('/foldersList')
def folderList():
    # Test is logged
    verify_ip()
    if auth_remote[request.remote_addr] == False:
        return redirect(url_for('login'))
    #Ver Pastas
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USERNAME, password=PASS)
    command = 'ls /smb'
    stdin, stdout, stderr = ssh.exec_command(command, get_pty = True)
    stdin.flush()
    # Decode the result
    result = stdout.read().decode("utf-8")
    # print(result)
    # Get all users excluding information from beggining
    folders  = result.split()
    # print(folders)
    for folder in REMOVE_FOLDERS:
        folders.remove(folder)
    # Get total of folders
    total_folders = len(folders)
    add_text = ''
    for folder in folders:
        add_text += f'/smb/{folder} '

    command = f'du -sh {add_text}'
    stdin, stdout, stderr = ssh.exec_command(command, get_pty = True)
    stdin.flush()
    # Decode the result
    result = stdout.read().decode("utf-8")
    folders = result.split("\n")

    command = f'du -sh /smb'
    stdin, stdout, stderr = ssh.exec_command(command, get_pty = True)
    stdin.flush()
    # Decode the result
    total = stdout.read().decode("utf-8")
    return render_template('foldersList.html', folders=folders, total=total)

@app.route('/folderUsers/<folder>', methods=['GET', 'POST'])
def folderUser(folder):
    # Test is logged
    verify_ip()
    if auth_remote[request.remote_addr] == False:
        return redirect(url_for('login'))
    #Ver Pastas
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USERNAME, password=PASS)
    command = 'sudo pdbedit -L'
    stdin, stdout, stderr = ssh.exec_command(command, get_pty = True)
    stdin.write(PASS+'\n')
    stdin.flush()
    # Decode the result
    result = stdout.read().decode("utf-8")
    # Get all users excluding information from beggining
    users  = result.split()[5:]
    # Get all users without unnecessary information
    users = [user.split(':')[0] for user in users]
    # Sort users
    users.sort()
    usuarios = ''
    for user in users:
        usuarios += f'{user} '

    # print(usuarios)
    command = f'sudo groups {usuarios}'
    stdin, stdout, stderr = ssh.exec_command(command, get_pty = True)
    stdin.write(PASS+'\n')
    stdin.flush()
    result = stdout.read().decode("utf-8")
    acessos = result.split('\n')
    users = []
    for acesso in acessos:
        if folder in acesso.split():
            users.append(acesso.split(" : ")[0])
        # if folder in result.split():
        #     print(user)
    # print(users)
    total = len(users)
    return render_template('usersList.html', users=users, total=total, name=folder)

@app.route('/addUser', methods=['GET', 'POST'])
def addUser():
    # Test is logged
    verify_ip()
    if auth_remote[request.remote_addr] == False:
        return redirect(url_for('login'))
    if request.method == 'POST':
        return render_template('hello.html', user=request.form['user'])
    else:
        return render_template('hello.html')

@app.route('/usersAdd', methods=['GET', 'POST'])
def adicionarUsuarios():
    # Test is logged
    verify_ip()
    if auth_remote[request.remote_addr] == False:
        return redirect(url_for('login'))
    if request.method == 'POST':
        if (request.form['username'] != "" and request.form['password'] != ""):
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(HOST, username=USERNAME, password=PASS)           
            command = f'sudo useradd {request.form["username"]}'
            stdin, stdout, stderr = ssh.exec_command(command, get_pty = True)
            stdin.write(PASS+'\n')
            stdin.flush()
            response = stdout.read().decode("utf-8")
            if ('already exists' in response):
                command = f'sudo smbpasswd -a {request.form["username"]}'
                stdin, stdout, stderr = ssh.exec_command(command, get_pty = True)
                time.sleep(1)
                stdin.write(PASS+'\n')
                time.sleep(1)
                stdin.write(request.form['password']+'\n')
                time.sleep(1)
                stdin.write(request.form['password']+'\n')
            else:
                command = f'sudo smbpasswd -a {request.form["username"]}'
                stdin, stdout, stderr = ssh.exec_command(command, get_pty = True)
                time.sleep(1)
                stdin.write(PASS+'\n')
                time.sleep(1)
                stdin.write(request.form['password']+'\n')
                time.sleep(1)
                stdin.write(request.form['password']+'\n')        
            return redirect(f'/userGroups/{request.form["username"]}')
    else:
        return render_template('usersAdd.html')

@app.route('/permissaoPastas')
def permissaoPastas():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USERNAME, password=PASS)
    command = 'sudo chmod -R 777 /smb/'
    stdin, stdout, stderr = ssh.exec_command(command, get_pty = True)
    stdin.write(PASS+'\n')
    stdin.flush()
    time.sleep(120)
    return redirect("/")

@app.route('/rebootSamba')
def rebootSamba():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USERNAME, password=PASS)
    command = 'sudo service smbd restart'
    stdin, stdout, stderr = ssh.exec_command(command, get_pty = True)
    stdin.write(PASS+'\n')
    stdin.flush()
    time.sleep(10)
    return redirect("/")

@app.route("/certificado")
def certificado():
    # Test is logged
    verify_ip()
    if auth_remote[request.remote_addr] == False:
        return redirect(url_for('login'))
    return render_template("certificado.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    # print(auth_remote[request.remote_addr])
    verify_ip()
    print(auth_remote)
    if request.method == 'POST':
        global is_authenticated
        error = None
        username = request.form['username']
        password = request.form['password']

        if not username:
            error = "Username is required"
        elif not password:
            error = "Password is required"
        if error is None:
            if username in users:
                if users[username] == request.form['password']:
                    auth_remote[request.remote_addr] = True
                    return redirect(url_for('index'))
                else:
                    print('Wrong Password')
            else:
                print("User does not exist")

        return render_template("login.html")
    else:
        return render_template("login.html")

if __name__ == "__main__":
    # Run with debug=True and host to access from another computer
    app.run(debug=True, host='0.0.0.0', port=5000)