import uvicorn
from decimal import Decimal
from fastapi import FastAPI, Query, Path, File, UploadFile, status, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl


app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def get_root():
    return {"Hello": "Worlod"}


@app.get("/items/{item_id}")
def get_item_by_id(
    item_id: int = Path(
        title="The ID of the item to get",
        ge=1
    ),
    needly: str = Query(min_length=5),
    q: list[str] | None = Query(
        default=None,
        title="Query string",
        description="Query string for the items to search in the database that have a good match.",
        alias="item-query",
        min_length=3,
        max_length=10,
        deprecated=True
    ),
    short: bool = False
):
    item = {"item_id": item_id, "needly": needly}

    if q:
        item.update({"q": q})

    if not short:
        item.update(
            {"description": "This is an amazing item that has a long description"}
        )

    return item


@app.get("/users/{user_id}/items/{item_id}")
def get_user_item_by_id(
    user_id: int,
    item_id: int,
    q: str | None = None,
    short: bool = False
):
    item = {"item_id": item_id, "owner_id": user_id}

    if q:
        item.update({"q": q})

    if not short:
        item.update(
            {"description": "This is an amazing item that has a long description"}
        )

    return item


fake_items_db = [{"item_name": "Foo"}, {"item_name": "Bar"}, {"item_name": "Baz"}]


@app.get("/items")
async def get_items(skip: int = 0, limit: int = 10):
    return fake_items_db[skip : skip + limit]


class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"


@app.get("/models/{model_name}")
async def getmodel(model_name: ModelName):
    if model_name is ModelName.alexnet:
        return {"model_name": model_name, "message": "Deep Learning FTW!"}
        
    if model_name == "lenet":
        return {"model_name": model_name, "message": "LeCNN all the images"}

    return {"model_name": model_name, "message": "Have some residuals"}


class Image(BaseModel):
    url: HttpUrl
    name: str


class Item(BaseModel):
    name: str
    description: str | None = Field(
        default=None,
        title="The description of the item",
        max_length=300
    )
    price: Decimal = Field(
        description="The price must be greater than 0.",
        gt=0
    )
    tax: Decimal | None = Field(
        default=None,
        description="Optional.The tax must be greater than 0."
    )
    tags: set[str] = set()
    image: list[Image] | None = None


@app.post("/items", status_code=status.HTTP_201_CREATED)
async def create_item(item: Item):
    if not item.tax:
        return item

    price_with_tax = item.price * (item.tax / Decimal(100) + Decimal(1))
    item_dict = item.dict()
    item_dict.update({"price_with_tax": price_with_tax})

    return item_dict


@app.put("/items/{item_id}", status_code=status.HTTP_201_CREATED)
async def put_item(
    item_id: int,
    item: Item,
    q: str | None = None
):
    result = {"item_id": item_id, **item.dict()}

    if q:
        result.update({"q": q})
    
    return result

@app.get("/files/size")
async def get_filesize(file: bytes = File()):
    return {"file_size": len(file)}

@app.put("/files/upload")
async def put_file(file: UploadFile):
    return {"file_name": file.filename}


fake_user_db = {
    "johndoe": {
        "membername": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "fakehashedsecret1",
        "disabled": False
    },
    "alice": {
        "membername": "alice",
        "full_name": "Alice Wonderson",
        "email": "alice@example.com",
        "hashed_password": "fakehashedsecret2",
        "disabled": True
    }
}


def fake_hash_password(password: str):
    return "fakehashed" + password


oauth2_schema = OAuth2PasswordBearer(tokenUrl="token")


class Member(BaseModel):
    membername: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None

class MemberInDB(Member):
    hashed_password: str

def get_member(db, membername: str):
    if membername in db:
        member_dict = db[membername]
        return MemberInDB(**member_dict)

def fake_decode_token(token):
    member = get_member(fake_user_db, token)
    return member


async def get_current_menber(token: str = Depends(oauth2_schema)):
    member = fake_decode_token(token)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return member


async def get_current_active_member(current_member: Member = Depends(get_current_menber)):
    if current_member.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive member"
        )
    return current_member


@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    member_dict = fake_user_db.get(form_data.username)

    if not member_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password"
        )

    member = MemberInDB(**member_dict)
    hashed_password = fake_hash_password(form_data.password)
    if not hashed_password == member.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password"
        )
    
    return {"access_token": member.membername, "token_type": "bearer"}

@app.get("/users/me")
async def get_me(current_member: Member = Depends(get_current_active_member)):
    return current_member



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

