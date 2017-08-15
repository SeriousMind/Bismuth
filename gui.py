# icons created using http://www.winterdrache.de/freeware/png2ico/
import PIL.Image, PIL.ImageTk, pyqrcode, os, hashlib, sqlite3, time, base64, connections, icons, log, socks, ast, options, math

(port, genesis_conf, verify_conf, version_conf, thread_limit_conf, rebuild_db_conf, debug_conf, purge_conf, pause_conf, ledger_path_conf, hyperblocks_conf, warning_list_limit_conf, tor_conf, debug_level_conf, allowed, pool_ip_conf, sync_conf, mining_threads_conf, diff_recalc_conf, pool_conf, pool_address, ram_conf, pool_percentage_conf, node_ip_conf) = options.read()

# port = 0000

from datetime import datetime
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA
from simplecrypt import encrypt, decrypt
from tkinter import *

global key
global encrypted
global unlocked

# for local evaluation
conn = sqlite3.connect('static/ledger.db')
conn.text_factory = str
global c
c = conn.cursor()

conn2 = sqlite3.connect('static/ledger.db')
conn2.text_factory = str
global c2
c2 = conn.cursor()

if not os.path.exists('mempool.db'):
    # create empty mempool
    mempool = sqlite3.connect('mempool.db',timeout=1)
    mempool.text_factory = str
    m = mempool.cursor()
    execute(m, ("CREATE TABLE IF NOT EXISTS transactions (timestamp, address, recipient, amount, signature, public_key, keep, openfield)"))
    commit(mempool)
    app_log.info("Created mempool file")
    # create empty mempool
else:
    mempool = sqlite3.connect('mempool.db', timeout=1)
    mempool.text_factory = str
    m = mempool.cursor()

# for local evaluation
# load config
lines = [line.rstrip('\n') for line in open('config.txt')]
for line in lines:
    if "debug_level=" in line:
        debug_level_conf = line.strip('debug_level=')
# load config

app_log = log.log("gui.log", debug_level_conf)

root = Tk()
root.wm_title("Bismuth")

def percentage(percent, whole):
    return float((percent * whole) / 100)

def execute(cursor, what):
    # secure execute for slow nodes
    passed = 0
    while passed == 0:
        try:
            # print cursor
            # print what

            cursor.execute(what)
            passed = 1
        except Exception as e:
            app_log.warning("Retrying database execute due to {}".format(e))
            time.sleep(random.random())
            pass
            # secure execute for slow nodes
    return cursor


def execute_param(cursor, what, param):
    # secure execute for slow nodes
    passed = 0
    while passed == 0:
        try:
            # print cursor
            # print what
            cursor.execute(what, param)
            passed = 1
        except Exception as e:
            app_log.warning("Retrying database execute due to " + str(e))
            time.sleep(0.1)
            pass
            # secure execute for slow nodes
    return cursor

def bin_convert(string):
    return ''.join(format(ord(x), '8b').replace(' ', '0') for x in string)

def difficulty(c):
    execute(c, "SELECT * FROM transactions ORDER BY block_height DESC LIMIT 1")
    result = c.fetchall()[0]
    timestamp_last = float(result[1])
    block_height = int(result[0])

    execute_param(c, ("SELECT block_height FROM transactions WHERE CAST(timestamp AS INTEGER) > ? AND reward != 0"), (timestamp_last - 86400,))  # 86400=24h
    blocks_per_1440 = len(c.fetchall())
    app_log.warning("Blocks per day: {}".format(blocks_per_1440))

    execute(c, ("SELECT difficulty FROM misc ORDER BY block_height DESC LIMIT 1"))
    try:
        diff_block_previous = float(c.fetchone()[0])
    except:
        diff_block_previous = 45

    try:
        log = math.log2(blocks_per_1440 / 1440)
    except:
        log = math.log2(0.5 / 1440)
    app_log.info("Difficulty retargeting: {}".format(log))

    difficulty = diff_block_previous + log  # increase/decrease diff by a little

    time_now = time.time()
    if time_now > timestamp_last + 300: #if 5 minutes have passed
        difficulty2 = percentage(97,difficulty)
    else:
        difficulty2 = difficulty

    if difficulty < 45 or difficulty2 < 45:
        difficulty = 45
        difficulty2 = 45

    app_log.warning("Difficulty: {}".format(difficulty2))

    return (float(difficulty), float(difficulty2))

def alias():
    alias_var = StringVar()

    # enter password
    top8 = Toplevel()
    top8.title("Enter Desired Name")

    alias_label = Label(top8, text="Input name")
    alias_label.grid(row=0, column=0, sticky=N + W, padx=15, pady=(5, 0))

    input_alias = Entry(top8, textvariable=alias_var)
    input_alias.grid(row=1, column=0, sticky=N + E, padx=15, pady=(0, 5))

    dismiss = Button(top8, text="Register", command=lambda: alias_register(alias_var.get().strip()))
    dismiss.grid(row=2, column=0, sticky=W + E, padx=15, pady=(15, 0))

    dismiss = Button(top8, text="Dismiss", command=top8.destroy)
    dismiss.grid(row=3, column=0, sticky=W + E, padx=15, pady=(5, 5))


def alias_register(alias_desired):
    reg_string = "alias=" + alias_desired

    conn = sqlite3.connect('static/ledger.db')
    conn.text_factory = str
    c = conn.cursor()

    m.execute("SELECT timestamp FROM transactions WHERE openfield = ?;", (reg_string,))
    registered_pending = m.fetchone()

    c.execute("SELECT timestamp FROM transactions WHERE openfield = ?;", (reg_string,))
    registered_already = c.fetchone()

    if registered_already == None and registered_pending == None:
        alias_cb_var.set(0)
        send_confirm("0", address, "1", reg_string)

    else:
        top9 = Toplevel()
        top9.title("Name already registered")

        registered_label = Label(top9, text="Name already registered")
        registered_label.grid(row=0, column=0, sticky=N + W, padx=15, pady=(5, 0))
        dismiss = Button(top9, text="Dismiss", command=top9.destroy)
        dismiss.grid(row=3, column=0, sticky=W + E, padx=15, pady=(5, 5))


def encrypt_get_password():
    # enter password
    top3 = Toplevel()
    top3.title("Enter Password")

    password_label = Label(top3, text="Input password")
    password_label.grid(row=0, column=0, sticky=N + W, padx=15, pady=(5, 0))

    input_password = Entry(top3, textvariable=password_var_enc, show='*')
    input_password.grid(row=1, column=0, sticky=N + E, padx=15, pady=(0, 5))

    confirm_label = Label(top3, text="Confirm password")
    confirm_label.grid(row=2, column=0, sticky=N + W, padx=15, pady=(5, 0))

    input_password_con = Entry(top3, textvariable=password_var_con, show='*')
    input_password_con.grid(row=3, column=0, sticky=N + E, padx=15, pady=(0, 5))

    enter = Button(top3, text="Encrypt", command=lambda: encrypt_fn(top3))
    enter.grid(row=4, column=0, sticky=W + E, padx=15, pady=(5, 5))

    cancel = Button(top3, text="Cancel", command=top3.destroy)
    cancel.grid(row=5, column=0, sticky=W + E, padx=15, pady=(5, 5))
    # enter password


def lock_fn(button):
    global key
    del key
    decrypt_b.configure(text="Unlock", state=NORMAL)
    lock_b.configure(text="Locked", state=DISABLED)
    password_var_dec.set("")


def encrypt_fn(destroy_this):
    password = password_var_enc.get()
    password_conf = password_var_con.get()

    if password == password_conf:


        ciphertext = encrypt(password, private_key_readable)

        pem_file = open("privkey_encrypted.der", 'wb')
        pem_file.write(base64.b64encode(ciphertext))
        pem_file.close()

        encrypt_b.configure(text="Encrypted", state=DISABLED)
        destroy_this.destroy()
        os.remove("privkey.der")
        lock_b.configure(text="Lock", state=NORMAL)
    else:
        mismatch = Toplevel()
        mismatch.title("Bismuth")

        mismatch_msg = Message(mismatch, text="Password mismatch", width=100)
        mismatch_msg.pack()

        mismatch_button = Button(mismatch, text="Continue", command=mismatch.destroy)
        mismatch_button.pack(padx=15, pady=(5, 5))


def decrypt_get_password():
    # enter password
    top4 = Toplevel()
    top4.title("Enter Password")

    input_password = Entry(top4, textvariable=password_var_dec, show='*')
    input_password.grid(row=0, column=0, sticky=N + E, padx=15, pady=(5, 5))

    enter = Button(top4, text="Unlock", command=lambda: decrypt_fn(top4))
    enter.grid(row=1, column=0, sticky=W + E, padx=15, pady=(5, 5))

    cancel = Button(top4, text="Cancel", command=top4.destroy)
    cancel.grid(row=2, column=0, sticky=W + E, padx=15, pady=(5, 5))
    # enter password


def decrypt_fn(destroy_this):
    global key
    try:
        password = password_var_dec.get()
        encrypted_privkey = open('privkey_encrypted.der', 'rb').read()
        decrypted_privkey = decrypt(password, base64.b64decode(encrypted_privkey))

        key = RSA.importKey(decrypted_privkey)  # be able to sign
        # print key
        decrypt_b.configure(text="Unlocked", state=DISABLED)
        lock_b.configure(text="Lock", state=NORMAL)
        destroy_this.destroy()
    except:
        top6 = Toplevel()
        top6.title("Locked")
        Label(top6, text="Wrong password", width=20).grid(row=0, pady=0)
        cancel = Button(top6, text="Cancel", command=top6.destroy)
        cancel.grid(row=1, column=0, sticky=W + E, padx=15, pady=(5, 5))

    return key


def send_confirm(amount_input, recipient_input, keep_input, openfield_input):
    top10 = Toplevel()
    top10.title("Confirm")

    # encr check
    if encrypt_var.get() == 1:
        #get recipient's public key
        c.execute("SELECT public_key FROM transactions WHERE address = ? and reward = 0",(recipient_input,))
        target_public_key_hashed = c.fetchone()[0]

        target_public_key = RSA.importKey(base64.b64decode(target_public_key_hashed).decode("utf-8"))


        openfield_input = str(target_public_key.encrypt(openfield_input.encode("utf-8"), 32))
    # encr check

    # msg check

    if encode_var.get() == 1:
        openfield_input = base64.b64encode(openfield_input.encode("utf-8")).decode("utf-8")

    # msg check
    if msg_var.get() == 1 and encode_var.get() == 1:
        openfield_input = "bmsg=" + openfield_input
    if msg_var.get() == 1 and encode_var.get() == 0:
        openfield_input = "msg=" + openfield_input


    if encrypt_var.get() == 1:
        openfield_input = "enc=" + str(openfield_input)



    fee = '%.8f' % float(0.01 + (float(amount.get()) * 0.001) + (float(len(openfield_input)) / 100000) + (float(keep_var.get()) / 10))  # 0.1% + 0.01 dust
    confirmation_dialog = Text(top10, width=100)
    confirmation_dialog.insert(INSERT, ("Amount: {}\nTo: {}\nFee: {}\nKeep Entry: {}\nOpenField:\n\n{}".format(amount_input, recipient_input, fee, keep_input, openfield_input)))

    confirmation_dialog.grid(row=0, pady=0)

    enter = Button(top10, text="Confirm", command=lambda: send(amount_input, recipient_input, keep_input, openfield_input, top10))
    enter.grid(row=1, column=0, sticky=W + E, padx=15, pady=(5, 5))

    done = Button(top10, text="Cancel", command=top10.destroy)
    done.grid(row=2, column=0, sticky=W + E, padx=15, pady=(5, 5))


def send(amount_input, recipient_input, keep_input, openfield_input, top10):
    try:
        key
    except:
        top5 = Toplevel()
        top5.title("Locked")

        Label(top5, text="Wallet is locked", width=20).grid(row=0, pady=0)

        done = Button(top5, text="Cancel", command=top5.destroy)
        done.grid(row=1, column=0, sticky=W + E, padx=15, pady=(5, 5))

    app_log.warning("Received tx command")

    try:
        float(amount_input)
    except:
        top7 = Toplevel()
        top7.title("Invalid amount")
        Label(top7, text="Amount must be a number", width=20).grid(row=0, pady=0)
        done = Button(top7, text="Cancel", command=top7.destroy)
        done.grid(row=1, column=0, sticky=W + E, padx=15, pady=(5, 5))

    # alias check
    if alias_cb_var.get() == 1:
        c.execute("SELECT address FROM transactions WHERE openfield = ? ORDER BY block_height ASC, timestamp ASC LIMIT 1;", ("alias=" + recipient_input,))  # asc for first entry
        recipient_input = c.fetchone()[0]
        app_log.warning("Fetched the following alias recipient: {}".format(recipient_input))
    # alias check

    if len(recipient_input) != 56:
        top6 = Toplevel()
        top6.title("Invalid address")
        Label(top6, text="Wrong address length", width=20).grid(row=0, pady=0)
        done = Button(top6, text="Cancel", command=top6.destroy)
        done.grid(row=1, column=0, sticky=W + E, padx=15, pady=(5, 5))
    else:

        app_log.warning("Amount: {}".format(amount_input))
        app_log.warning("Recipient: {}".format(recipient_input))
        app_log.warning("Keep Forever: {}".format(keep_input))
        app_log.warning("OpenField Data: {}".format(openfield_input))

        timestamp = '%.2f' % time.time()
        transaction = (str(timestamp), str(address), str(recipient_input), '%.8f' % float(amount_input), str(keep_input), str(openfield_input))  # this is signed

        h = SHA.new(str(transaction).encode("utf-8"))
        signer = PKCS1_v1_5.new(key)
        signature = signer.sign(h)
        signature_enc = base64.b64encode(signature)
        app_log.warning("Client: Encoded Signature: {}".format(signature_enc.decode("utf-8")))

        verifier = PKCS1_v1_5.new(key)
        if verifier.verify(h, signature) == True:
            if float(amount_input) < 0:
                app_log.warning("Client: Signature OK, but cannot use negative amounts")

            elif (float(amount_input) > float(balance)):
                app_log.warning("Mempool: Sending more than owned")

            else:
                app_log.warning("Client: The signature is valid, proceeding to save transaction, signature, new txhash and the public key to mempool")

                # print(str(timestamp), str(address), str(recipient_input), '%.8f' % float(amount_input),str(signature_enc), str(public_key_hashed), str(keep_input), str(openfield_input))
                m.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)", (str(timestamp), str(address), str(recipient_input), '%.8f' % float(amount_input), str(signature_enc.decode("utf-8")), str(public_key_hashed.decode("utf-8")), str(keep_input), str(openfield_input)))
                mempool.commit()  # Save (commit) the changes
                app_log.warning("Client: Mempool updated with a received transaction")
                # refresh() experimentally disabled
        else:
            app_log.warning("Client: Invalid signature")
        # enter transaction end

        top10.destroy()
        # refresh() experimentally disabled


def app_quit():
    if conn:
        conn.close()
    if mempool:
        mempool.close()

    app_log.warning("Received quit command")
    root.destroy()


def qr():
    address_qr = pyqrcode.create(address)
    address_qr.png('address_qr.png')

    # popup
    top = Toplevel()
    top.wm_iconbitmap(tempFile)
    top.title("Address QR Code")

    im = PIL.Image.open("address_qr.png")

    photo = PIL.ImageTk.PhotoImage(im.resize((320, 320)))
    label = Label(top, image=photo)
    label.image = photo  # keep a reference!
    label.pack()

    # msg = Message(top, text="hi")
    # msg.pack()

    button = Button(top, text="Dismiss", command=top.destroy)
    button.pack()
    # popup


def msg_dialogue():
    def msg_received_get():

        for row in c.execute("SELECT address,openfield,timestamp FROM transactions WHERE recipient = ? AND (openfield LIKE ? OR openfield LIKE ? OR openfield LIKE ? OR openfield LIKE ?) ORDER BY timestamp DESC;", (address,) + ("msg=" + '%',) + ("bmsg=" + '%',) + ("enc=msg=" + '%',) + ("enc=bmsg=" + '%',)):

            # get alias
            try:
                c2.execute("SELECT openfield FROM transactions WHERE openfield LIKE ? AND address = ? ORDER BY block_height ASC, timestamp ASC LIMIT 1;", ("alias=" + '%', row[0],))  # asc for first entry
                msg_address = c2.fetchone()[0]
            # get alias
            except:
                msg_address = row[0]


            if row[1].startswith("enc=msg="):
                msg_received_digest = row[1].lstrip("enc=msg=")
                try:
                    msg_received_digest = key.decrypt(ast.literal_eval(msg_received_digest)).decode("utf-8")
                except:
                    msg_received_digest = "Could not decrypt message"

            elif row[1].startswith("enc=bmsg="):
                msg_received_digest = row[1].lstrip("enc=bmsg=")
                try:
                    msg_received_digest = base64.b64decode(msg_received_digest).decode("utf-8")
                    msg_received_digest = key.decrypt(ast.literal_eval(msg_received_digest)).decode("utf-8")
                except:
                    msg_received_digest = "Could not decrypt message"

            elif row[1].startswith("bmsg="):
                msg_received_digest = row[1].lstrip("bmsg=")
                try:
                    msg_received_digest = base64.b64decode(msg_received_digest).decode("utf-8")
                except:
                    msg_received_digest = "Could not decode message"
            elif row[1].startswith("msg="):
                msg_received_digest = row[1].lstrip("msg=")




            msg_received.insert(INSERT, ((time.strftime("%Y/%m/%d,%H:%M:%S", time.gmtime(float(row[2])))) + " From " + msg_address.replace("alias=", "") + ": " + msg_received_digest) + "\n")

    def msg_sent_get():

        for row in c.execute("SELECT recipient,openfield,timestamp FROM transactions WHERE address = ? AND (openfield LIKE ? OR openfield LIKE ? OR openfield LIKE ? OR openfield LIKE ?) ORDER BY timestamp DESC;", (address,) + ("msg=" + '%',) + ("bmsg=" + '%',) + ("enc=msg=" + '%',) + ("enc=bmsg=" + '%',)):
            try:
                # get alias
                c2.execute("SELECT openfield FROM transactions WHERE openfield LIKE ? AND address = ? ORDER BY block_height ASC, timestamp ASC LIMIT 1;", ("alias=" + '%', row[0],))  # asc for first entry
                msg_recipient = c2.fetchone()[0]
                # get alias
            except:
                msg_recipient = row[0]

            if row[1].startswith("enc=msg="):
                msg_sent_digest = row[1].lstrip("enc=msg=")
                try:
                    msg_sent_digest = key.decrypt(ast.literal_eval(msg_sent_digest)).decode("utf-8")
                except:
                    msg_sent_digest = "Could not decrypt message"

            elif row[1].startswith("enc=bmsg="):
                msg_sent_digest = row[1].lstrip("enc=bmsg=")
                try:
                    msg_sent_digest = base64.b64decode(msg_sent_digest).decode("utf-8")
                    msg_sent_digest = key.decrypt(ast.literal_eval(msg_sent_digest)).decode("utf-8")
                except:
                    msg_sent_digest = "Could not decrypt message"

            elif row[1].startswith("bmsg="):
                msg_sent_digest = row[1].lstrip("bmsg=")
                try:
                    msg_sent_digest = base64.b64decode(msg_sent_digest).decode("utf-8")
                except:
                    msg_received_digest = "Could not decode message"

            elif row[1].startswith("msg="):
                msg_sent_digest = row[1].lstrip("msg=")

            msg_sent.insert(INSERT, ((time.strftime("%Y/%m/%d,%H:%M:%S", time.gmtime(float(row[2])))) + " To " + msg_recipient.replace("alias=", "") + ": " + msg_sent_digest) + "\n")

    # popup
    top11 = Toplevel()
    top11.title("Messaging")

    Label(top11, text="Received:", width=20).grid(row=0)

    msg_received = Text(top11, width=100, height=20, font=("Tahoma", 8))
    msg_received.grid(row=1, column=0, sticky=W, padx=5, pady=(5, 5))
    msg_received_get()

    Label(top11, text="Sent:", width=20).grid(row=2)

    msg_sent = Text(top11, width=100, height=20, font=("Tahoma", 8))
    msg_sent.grid(row=3, column=0, sticky=W, padx=5, pady=(5, 5))
    msg_sent_get()

    dismiss = Button(top11, text="Dismiss", command=top11.destroy)
    dismiss.grid(row=5, column=0, sticky=W + E, padx=15, pady=(5, 5))

    # popup


def sign():
    def verify_this():
        try:
            received_public_key = RSA.importKey(public_key_gui.get("1.0", END))
            verifier = PKCS1_v1_5.new(received_public_key)
            h = SHA.new(input_text.get("1.0", END).encode("utf-8"))
            received_signature_dec = base64.b64decode(output_signature.get("1.0", END))

            if verifier.verify(h, received_signature_dec) == True:
                top2 = Toplevel()
                top2.title("Validation results")
                msg = Message(top2, text="Signature Valid", width=50)
                msg.pack()
                button = Button(top2, text="Dismiss", command=top2.destroy)
                button.pack()
            else:
                raise
        except:
            top2 = Toplevel()
            top2.title("Validation results")
            msg = Message(top2, text="Signature Invalid", width=50)
            msg.pack()
            button = Button(top2, text="Dismiss", command=top2.destroy)
            button.pack()

    def sign_this():
        h = SHA.new(input_text.get("1.0", END).encode("utf-8"))
        signer = PKCS1_v1_5.new(key)
        signature = signer.sign(h)
        signature_enc = base64.b64encode(signature)

        output_signature.delete('1.0', END)  # remove previous
        output_signature.insert(INSERT, signature_enc)

    # popup
    top = Toplevel()
    top.title("Sign message")
    # top.geometry("%dx%d%+d%+d" % (800, 600, 0, 0))
    # top.grid_propagate(False)

    Label(top, text="Message:", width=20).grid(row=0, pady=0)
    input_text = Text(top, height=10)
    # label.image = photo  # keep a reference!
    input_text.grid(row=1, column=0, sticky=N + E, padx=15, pady=(0, 0))

    Label(top, text="Public Key:", width=20).grid(row=2, pady=0)
    public_key_gui = Text(top, height=10)
    public_key_gui.insert(INSERT, public_key_readable)
    public_key_gui.grid(row=3, column=0, sticky=N + E, padx=15, pady=(0, 0))

    Label(top, text="Signature:", width=20).grid(row=4, pady=0)
    output_signature = Text(top, height=10)
    output_signature.grid(row=5, column=0, sticky=N + E, padx=15, pady=(0, 0))

    # msg = Message(top, text="hi")
    # msg.pack()

    sign_message = Button(top, text="Sign Message", command=sign_this)
    sign_message.grid(row=6, column=0, sticky=W + E, padx=15, pady=(5, 0))

    sign_message = Button(top, text="Verify Message", command=verify_this)
    sign_message.grid(row=7, column=0, sticky=W + E, padx=15, pady=(15, 0))

    dismiss = Button(top, text="Dismiss", command=top.destroy)
    dismiss.grid(row=8, column=0, sticky=W + E, padx=15, pady=(15, 5))
    # popup


def refresh_auto():
    root.after(0, refresh)
    root.after(30000, refresh_auto)


def table():
    # transaction table
    # data

    datasheet = ["Time", "From", "To", "Amount", "Type"]

    rows_total = 19

    for row in m.execute("SELECT * FROM transactions WHERE address = ? OR recipient = ? ORDER BY timestamp DESC LIMIT 19;", (address,) + (address,)):
        rows_total = rows_total - 1

        # mempool_timestamp = row[1]
        # datasheet.append(datetime.fromtimestamp(float(mempool_timestamp)).strftime('%Y-%m-%d %H:%M:%S'))
        datasheet.append("Unconfirmed")
        mempool_address = row[1]
        datasheet.append(mempool_address)
        mempool_recipient = row[2]
        datasheet.append(mempool_recipient)
        mempool_amount = row[3]
        datasheet.append(mempool_amount)
        symbol = " Transaction"
        datasheet.append(symbol)

    for row in c.execute("SELECT * FROM transactions WHERE address = ? OR recipient = ? ORDER BY block_height DESC LIMIT ?;", (address,) + (address,) + (rows_total,)):
        db_timestamp = row[1]
        datasheet.append(datetime.fromtimestamp(float(db_timestamp)).strftime('%Y-%m-%d %H:%M:%S'))
        db_address = row[2]
        datasheet.append(db_address)
        db_recipient = row[3]
        datasheet.append(db_recipient)
        db_amount = row[4]
        db_reward = row[9]
        db_openfield = row[11]
        datasheet.append('%.8f' % (float(db_amount) + float(db_reward)))
        if float(db_reward) > 0:
            symbol = " Mined"
        elif db_openfield.startswith("bmsg"):
            symbol = " b64 Message"
        elif db_openfield.startswith("msg"):
            symbol = " Message"
        else:
            symbol = " Transaction"
        datasheet.append(symbol)
    # data

    app_log.warning(datasheet)
    app_log.warning(len(datasheet))

    if len(datasheet) == 5:
        app_log.warning("Looks like a new address")

    elif len(datasheet) < 20 * 5:
        app_log.warning(len(datasheet))
        table_limit = len(datasheet) / 5
    else:
        table_limit = 20

    if len(datasheet) > 5:
        k = 0

        for child in f4.winfo_children():  # prevent hangup
            child.destroy()

        for i in range(int(table_limit)):
            for j in range(5):

                e = Entry(f4, width=22)
                datasheet_compare = [datasheet[k], datasheet[k - 1], datasheet[k - 2], datasheet[k - 3], datasheet[k - 4]]

                if "Unconfirmed" in datasheet_compare:
                    e.configure(readonlybackground='linen')
                elif "Time" in datasheet_compare:
                    pass
                elif datasheet[k - 2] == address and j == 3:
                    e.configure(readonlybackground='indianred')
                elif datasheet[k - 1] == address and j == 3:
                    e.configure(readonlybackground='green4')
                else:
                    e.configure(readonlybackground='bisque')

                e.grid(row=i + 1, column=j, sticky=EW)
                e.insert(END, datasheet[k])
                e.configure(state="readonly")
                k = k + 1

                # transaction table
                # refreshables


def refresh():
    global balance

    # print "refresh triggered"

    try:
        s = socks.socksocket()
        s.connect((node_ip_conf, int(port)))
        connections.send(s, "balanceget", 10)
        connections.send(s, address, 10)  # change address here to view other people's transactions
        stats_account = connections.receive(s, 10)
        balance = stats_account[0]
        credit = stats_account[1]
        debit = stats_account[2]
        fees = stats_account[3]
        rewards = stats_account[4]

        app_log.warning("Transction address balance: {}".format(balance))

        connections.send(s, "blocklast", 10)
        block_get = connections.receive(s, 10)
        bl_height = block_get[0]
        db_timestamp_last = block_get[1]

        s.close()

    except:  # get locally
        app_log.warning("Unable to start in light mode, using local db for balance calculation")
        # global balance

        # print "refresh triggered"

        m.execute("SELECT sum(amount) FROM transactions WHERE address = ?;", (address,))
        debit_mempool = m.fetchone()[0]
        if debit_mempool == None:
            debit_mempool = 0

        c.execute("SELECT sum(amount) FROM transactions WHERE recipient = ?;", (address,))
        credit = c.fetchone()[0]
        c.execute("SELECT sum(amount) FROM transactions WHERE address = ?;", (address,))
        debit = c.fetchone()[0]
        c.execute("SELECT sum(fee) FROM transactions WHERE address = ?;", (address,))
        fees = c.fetchone()[0]
        c.execute("SELECT sum(reward) FROM transactions WHERE address = ?;", (address,))
        rewards = c.fetchone()[0]
        c.execute("SELECT MAX(block_height) FROM transactions")
        bl_height = c.fetchone()[0]

        if debit == None:
            debit = 0
        if fees == None:
            fees = 0
        if rewards == None:
            rewards = 0
        if credit == None:
            credit = 0
        balance = credit - debit - fees + rewards - debit_mempool
        app_log.warning("Node: Transction address balance: {}".format(balance))

        # calculate diff
        c.execute("SELECT * FROM transactions WHERE reward != 0 ORDER BY block_height DESC LIMIT 1;")  # or it takes the first
        result = c.fetchall()
        db_timestamp_last = float(result[0][1])
        # print db_timestamp_last
        db_block_height = result[0][0]
        # print timestamp_avg

    try:
        if encode_var.get() == 1:
            openfield_input = base64.b64encode(str(openfield.get("1.0", END).strip()))
        else:
            openfield_input = str(openfield.get("1.0", END)).strip()

        fee = '%.8f' % float(0.01 + (float(amount.get()) * 0.001) + (float(len(openfield_input)) / 100000) + (float(keep_var.get()) / 10))  # 0.1% + 0.01 dust

        app_log.warning("Fee: {}".format(fee))

    except Exception as e:
        fee = 0.01
        app_log.warning("Fee error: {}".format(e))
    # calculate fee


    # check difficulty
    try:
        s = socks.socksocket()
        s.connect((node_ip_conf, int(port)))
        connections.send(s, "diffget", 10)
        diff = connections.receive(s, 10)
        s.close()
    except:  # get locally
        app_log.warning("Unable to start in light mode, using local db for difficulty calculation")
        diff = difficulty(c)

    # check difficulty


    diff_msg = diff[1]

    # network status
    time_now = str(time.time())
    last_block_ago = float(time_now) - float(db_timestamp_last)
    if last_block_ago > 300:
        sync_msg = "{}m behind".format((int(last_block_ago / 60)))
        sync_msg_label.config(fg='red')
    else:
        sync_msg = "Up to date\nLast block: {}s ago".format((int(last_block_ago)))
        sync_msg_label.config(fg='green')

    # network status

    # aliases
    # c.execute("SELECT openfield FROM transactions WHERE address = ? AND openfield LIKE ?;",(address,)+("alias="+'%',))
    # aliases = c.fetchall()
    # app_log.warning("Aliases: "+str(aliases))
    # aliases

    # fees_current_var.set("Current Fee: {}".format('%.8f' % float(fee)))
    balance_var.set("Balance: {}".format('%.8f' % float(balance)))
    debit_var.set("Spent Total: {}".format('%.8f' % float(debit)))
    credit_var.set("Received Total: {}".format('%.8f' % float(credit)))
    fees_var.set("Fees Paid: {}".format('%.8f' % float(fees)))
    rewards_var.set("Rewards: {}".format('%.8f' % float(rewards)))
    bl_height_var.set("Block Height: {}".format(bl_height))
    diff_msg_var.set("Mining Difficulty: {}".format(diff_msg))
    sync_msg_var.set("Network: {}".format(sync_msg))

    table()
    # root.after(1000, refresh)


if "posix" not in os.name:
    # icon

    icondata = base64.b64decode(icons.icon_hash)
    ## The temp file is icon.ico
    tempFile = "icon.ico"
    iconfile = open(tempFile, "wb")
    ## Extract the icon
    iconfile.write(icondata)
    iconfile.close()
    root.wm_iconbitmap(tempFile)
    ## Delete the tempfile
    # icon

password_var_enc = StringVar()
password_var_con = StringVar()
password_var_dec = StringVar()

# import keys
if not os.path.exists('privkey_encrypted.der'):
    key = RSA.importKey(open('privkey.der').read())
    private_key_readable = key.exportKey().decode("utf-8")
    # public_key = key.publickey()
    encrypted = 0
    unlocked = 1
else:
    encrypted = 1
    unlocked = 0

# public_key_readable = str(key.publickey().exportKey())
public_key_readable = open('pubkey.der'.encode('utf-8')).read()

if (len(public_key_readable)) != 271:
    raise ValueError ("Invalid public key length")

public_key_hashed = base64.b64encode(public_key_readable.encode('utf-8'))
address = hashlib.sha224(public_key_readable.encode('utf-8')).hexdigest()

# frames
f2 = Frame(root, height=100, width=100)
f2.grid(row=0, column=1, sticky=W + E + N)

f3 = Frame(root, width=500)
f3.grid(row=0, column=0, sticky=W + E + N, pady=10, padx=10)

f4 = Frame(root, height=100, width=100)
f4.grid(row=1, column=0, sticky=W + E + N, pady=10, padx=10)

f5 = Frame(root, height=100, width=100)
f5.grid(row=1, column=1, sticky=W + E + N, pady=10, padx=10)

f6 = Frame(root, height=100, width=100)
f6.grid(row=2, column=0, sticky=E, pady=10, padx=10)
# frames


# buttons

send_b = Button(f5, text="Send", command=lambda: send_confirm(str(amount.get()).strip(), recipient.get().strip(), str(keep_var.get()).strip(), (openfield.get("1.0", END)).strip()), height=1, width=10)
send_b.grid(row=7, column=0, sticky=W + E + S, pady=(45, 2), padx=15)

start_b = Button(f5, text="Generate QR Code", command=qr, height=1, width=10)
if "posix" in os.name:
    start_b.configure(text="QR Disabled", state=DISABLED)
start_b.grid(row=8, column=0, sticky=W + E + S, pady=2, padx=15)

message_b = Button(f5, text="Manual Refresh", command=refresh, height=1, width=10)
message_b.grid(row=9, column=0, sticky=W + E + S, pady=2, padx=15)

balance_b = Button(f5, text="Messages", command=msg_dialogue, height=1, width=10)
balance_b.grid(row=10, column=0, sticky=W + E + S, pady=2, padx=15)

sign_b = Button(f5, text="Sign Message", command=sign, height=1, width=10)
sign_b.grid(row=11, column=0, sticky=W + E + S, pady=2, padx=15)

sign_b = Button(f5, text="Alias Registration", command=alias, height=1, width=10)
sign_b.grid(row=12, column=0, sticky=W + E + S, pady=2, padx=15)

quit_b = Button(f5, text="Quit", command=app_quit, height=1, width=10)
quit_b.grid(row=13, column=0, sticky=W + E + S, pady=0, padx=15)

encrypt_b = Button(f6, text="Encrypt", command=encrypt_get_password, height=1, width=10)
if encrypted == 1:
    encrypt_b.configure(text="Encrypted", state=DISABLED)
encrypt_b.grid(row=1, column=1, sticky=E + N, pady=0, padx=5)

decrypt_b = Button(f6, text="Unlock", command=decrypt_get_password, height=1, width=10)
if unlocked == 1:
    decrypt_b.configure(text="Unlocked", state=DISABLED)
decrypt_b.grid(row=1, column=2, sticky=E + N, pady=0, padx=5)

lock_b = Button(f6, text="Locked", command=lambda: lock_fn(lock_b), height=1, width=10, state=DISABLED)
if encrypted == 0:
    lock_b.configure(text="Lock", state=DISABLED)
lock_b.grid(row=1, column=3, sticky=E + N, pady=0, padx=5)

# buttons

# refreshables

# update balance label
balance_var = StringVar()
balance_msg_label = Label(f5, textvariable=balance_var)
balance_msg_label.grid(row=0, column=0, sticky=N + E, padx=15, pady=(0, 0))

debit_var = StringVar()
spent_msg_label = Label(f5, textvariable=debit_var)
spent_msg_label.grid(row=1, column=0, sticky=N + E, padx=15)

credit_var = StringVar()
received_msg_label = Label(f5, textvariable=credit_var)
received_msg_label.grid(row=2, column=0, sticky=N + E, padx=15)

fees_var = StringVar()
fees_paid_msg_label = Label(f5, textvariable=fees_var)
fees_paid_msg_label.grid(row=3, column=0, sticky=N + E, padx=15)

rewards_var = StringVar()
rewards_paid_msg_label = Label(f5, textvariable=rewards_var)
rewards_paid_msg_label.grid(row=4, column=0, sticky=N + E, padx=15)

# fees_current_var = StringVar()
# fees_to_pay_msg_label = Label(f5, textvariable=fees_current_var)
# fees_to_pay_msg_label.grid(row=5, column=0, sticky=N+E, padx=15)

bl_height_var = StringVar()
block_height_label = Label(f5, textvariable=bl_height_var)
block_height_label.grid(row=5, column=0, sticky=N + E, padx=15)

diff_msg_var = StringVar()
diff_msg_label = Label(f5, textvariable=diff_msg_var)
diff_msg_label.grid(row=6, column=0, sticky=N + E, padx=15)

sync_msg_var = StringVar()
sync_msg_label = Label(f5, textvariable=sync_msg_var)
sync_msg_label.grid(row=7, column=0, sticky=N + E, padx=15)

keep_var = IntVar()
encode_var = IntVar()
alias_cb_var = IntVar()
# encrypt_var = IntVar()
msg_var = IntVar()
encrypt_var = IntVar()

# address and amount
gui_address = Entry(f3, width=60)
gui_address.grid(row=0, column=1, sticky=W)
gui_address.insert(0, address)
gui_address.configure(state="readonly")

Label(f3, text="Your Address:", width=20, anchor="e").grid(row=0)
Label(f3, text="Recipient:", width=20, anchor="e").grid(row=1)
Label(f3, text="Amount:", width=20, anchor="e").grid(row=2)
Label(f3, text="Data:", width=20, anchor="e").grid(row=3)

recipient = Entry(f3, width=60)
recipient.grid(row=1, column=1, sticky=W)
amount = Entry(f3, width=60)
amount.insert(0, 0)
amount.grid(row=2, column=1, sticky=W)
openfield = Text(f3, width=60, height=5, font=("Tahoma", 8))
openfield.grid(row=3, column=1, sticky=W)

alias_cb = Checkbutton(f3, text="Alias", variable=alias_cb_var, command=None)
alias_cb.grid(row=4, column=1, sticky=E)

keep = Checkbutton(f3, text="Keep Entry", variable=keep_var)
keep.grid(row=4, column=1, sticky=E, padx=(0, 90))

encode = Checkbutton(f3, text="Base64", variable=encode_var)
encode.grid(row=4, column=1, sticky=E, padx=(0, 170))

msg = Checkbutton(f3, text="Message", variable=msg_var)
msg.grid(row=4, column=1, sticky=E, padx=(0, 230))

msg = Checkbutton(f3, text="Encrypt", variable=encrypt_var)
msg.grid(row=4, column=1, sticky=E, padx=(0, 300))

balance_enumerator = Entry(f3, width=5)
# address and amount

Label(f3, text="Your Latest Transactions:", width=20, anchor="w").grid(row=8, sticky=S)
Label(f3, text="", width=20, anchor="w").grid(row=7, sticky=S)

# logo

logo_hash_decoded = base64.b64decode(icons.logo_hash)
logo = PhotoImage(data=logo_hash_decoded)
image = Label(f2, image=logo).grid(pady=25, padx=50, sticky=N)
# logo

refresh_auto()
root.mainloop()

os.remove(tempFile)