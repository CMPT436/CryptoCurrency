#Hustone
#436 Project
#Client GUI Class
#*********************
# - A GUI for Client of Crypto Implementation
# Has functionality for seeing Balance and making transactions, and viewing transactions


import tkinter as tk
# import tkMessageBox
import tkinter.messagebox as tkMessageBox
import SHERcoin as c
import client as cli
import subprocess as sub

my_wallet = "wallet1.dat"


#Balance Button PopUp
def bal():
    balance = sub.check_output(['./client.py', 'balance', '-w', walletOption.get()])
    tkMessageBox.showinfo("Your Balance", balance)

#Send Coin
def sendit():
	sent = sub.check_output(['./client.py', 'send', '-w', walletOption.get(), sendAddy.get(), sendAmount.get()]))
	tkMessageBox.showinfo("Sending", sent)

#View Transaction	Status
def status():
	txStat = sub.check_output(['./client.py', 'status', txID.get()])
	tkMessageBox.showinfo("Your Balance", txStat)


##Tkinter GUI 
root = tk.Tk()
frame = tk.Frame(root)
frame.grid()

sendAmount = tk.StringVar()
sendAddy = tk.StringVar()
txID = tk.StringVar()
walletOption = tk.StringVar()

wallets = {'wallet1.dat', 'wallet2.dat', 'wallet3.dat', 'wallet4.dat'}



wallet_menu = tk.OptionMenu(frame, walletOption, *wallets)
wallet_menu.grid(row=0, column=0, sticky=tk.W)


button = tk.Button(frame,
                   text="QUIT",
                   fg="red",
                   command=quit)
button.grid(row=5, column=0, sticky=tk.W)

bal_butt = tk.Button(frame,
                   text="Balance",
                   command=bal)
bal_butt.grid(row=1, column=0, sticky=tk.W)

send_butt = tk.Button(frame,
                   text="Send",
                   command=sendit)
send_butt.grid(row=2, column=0, sticky=tk.W)

amountLabel = tk.Label(frame, text="Amount: ")
amountLabel.grid(row=2, column=1)

send_AmountEntry = tk.Entry(frame, textvariable=sendAmount)
send_AmountEntry.grid(row=2, column=2)

addyLabel = tk.Label(frame, text="Address: ")
addyLabel.grid(row=2, column=3)


send_AddyEntry = tk.Entry(frame, textvariable=sendAddy)
send_AddyEntry.grid(row=2, column=4)


stat_butt = tk.Button(frame,
                   text="View Status",
                   command=status)
stat_butt.grid(row=3, column=0, sticky=tk.W)

txLabel = tk.Label(frame, text="Address: ")
txLabel.grid(row=3, column=1)


stat_TxEntry = tk.Entry(frame, textvariable=txID)
stat_TxEntry.grid(row=3, column=2)

root.mainloop()
