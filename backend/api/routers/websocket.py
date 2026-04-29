import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.websocket_service import ws_manager

router = APIRouter(tags=['websocket'])


@router.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    reconnect_token = websocket.query_params.get('reconnect_token')
    await ws_manager.connect(websocket, reconnect_token=reconnect_token)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                action = message.get('action')

                if action == 'subscribe':
                    machine_ids = message.get('machine_ids', [])
                    for machine_id in machine_ids:
                        await ws_manager.subscribe_to_machine(websocket, int(machine_id))
                    await websocket.send_json(
                        {
                            'type': 'subscription_confirmed',
                            'machine_ids': ws_manager.get_subscriptions(websocket),
                        }
                    )
                elif action == 'unsubscribe':
                    machine_ids = message.get('machine_ids', [])
                    for machine_id in machine_ids:
                        await ws_manager.unsubscribe_from_machine(websocket, int(machine_id))
                    await websocket.send_json(
                        {
                            'type': 'unsubscription_confirmed',
                            'machine_ids': ws_manager.get_subscriptions(websocket),
                        }
                    )
                elif action == 'resume':
                    token = message.get('reconnect_token')
                    subscriptions = await ws_manager.resume_connection(websocket, token) if token else None
                    if subscriptions is None:
                        await websocket.send_json({'type': 'resume_failed', 'message': 'Invalid or expired token'})
                    else:
                        await websocket.send_json(
                            {
                                'type': 'resume_confirmed',
                                'reconnect_token': token,
                                'machine_ids': subscriptions,
                            }
                        )
                elif action == 'ping':
                    await websocket.send_json({'type': 'pong'})
                else:
                    await websocket.send_json({'type': 'error', 'message': f'Unknown action: {action}'})

            except json.JSONDecodeError:
                await websocket.send_json({'type': 'error', 'message': 'Invalid JSON format'})

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
