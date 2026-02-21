from aiortc import RTCPeerConnection, RTCSessionDescription
from ai_service import AudioReceiver

async def create_peer_connection(sdp_params, pcs_set, active_channels_set):
    """
    Crée, configure et renvoie une connexion WebRTC prête à l'emploi.
    
    Args:
        sdp_params (dict): Les params SDP/Type envoyés par le client.
        pcs_set (set): Ensemble global pour stocker les connexions PC.
        active_channels_set (set): Ensemble global pour stocker les DataChannels.
    """
    # 1. Création de la connexion
    pc = RTCPeerConnection()
    pcs_set.add(pc)

    # 2. Gestionnaire de DataChannel (Chat)
    @pc.on("datachannel")
    def on_datachannel(channel):
        active_channels_set.add(channel)
        print(f"[WebRTC] DataChannel ouvert: {channel.label}")
        
        @channel.on("close")
        def on_close():
            active_channels_set.discard(channel)

    # 3. Gestionnaire de Piste (Audio)
    @pc.on("track")
    def on_track(track):
        if track.kind == "audio":
            print("[WebRTC] Piste Audio détectée -> Branchement IA")
            # On injecte le Receiver qui contient toute l'IA
            pc.addTrack(AudioReceiver(track, active_channels_set))

    # 4. Gestionnaire d'État
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(f"[WebRTC] État: {pc.connectionState}")
        if pc.connectionState == "failed":
            await pc.close()
            pcs_set.discard(pc)

    # 5. Négociation SDP (Offer/Answer)
    offer = RTCSessionDescription(sdp=sdp_params["sdp"], type=sdp_params["type"])
    await pc.setRemoteDescription(offer)
    
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return pc