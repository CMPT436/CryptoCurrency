#TODO: imports

#get port variable from enviroment
PORT = os.environ.get('TC_PORT', 9999)

def main():
    #gets saved chain or we'll get a new one
    load_from_disk()

    #initializes the server and workers
    workers = []
    server = ThreadedTCPServer(('0.0.0.0', PORT), TCPHandler)

    
    def start_worker(fnc):
        workers.append(threading.Thread(target=fnc, daemon=True))
        workers[-1].start()


    logger.info(f'[p2p] listening on {PORT}')
    #start server worker
    start_worker(server.serve_forever)

    if peer_hostnames:
        logger.info(
            f'start initial block download from {len(peer_hostnames)} peers')
        send_to_peer(GetBlocksMsg(active_chain[-1].id))
        ibd_done.wait(60.)  # Wait a maximum of 60 seconds for IBD to complete.

    #start mining worker
    start_worker(mine_forever)
    #this makes main run until both workers dies
    [w.join() for w in workers]


if __name__ == '__main__':
    signing_key, verifying_key, my_address = init_wallet()
main()
