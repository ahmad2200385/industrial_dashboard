from fastapi import APIRouter

router = APIRouter(tags=['health'])


@router.get('/')
def home():
    return {'message': 'Smart Factory API Running'}
