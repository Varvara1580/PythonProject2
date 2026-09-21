# Импортируем FastAPI — главный класс, который создаёт веб-приложение (сайт/API)
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, File, UploadFile

# HTMLResponse — говорим FastAPI, что ответ будет HTML (страница)
# RedirectResponse — ответ-перенаправление (после POST обычно редиректят на GET)
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, FileResponse

# Jinja2Templates — подключаем шаблоны (HTML-файлы с подстановками {{ ... }})
from fastapi.templating import Jinja2Templates

from app.database import *
from app.services import *
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer

from app.Models import *
from datetime import datetime, timedelta, timezone, date


from matplotlib.figure import Figure
import io

from fastapi.staticfiles import StaticFiles

# Создаём приложение FastAPI (это “серверное” приложение)
app = FastAPI(title="Site without JS")


app.mount('/static', StaticFiles(directory = 'static'), name = 'static')
# Указываем папку, где лежат HTML-шаблоны
templates = Jinja2Templates(directory="templates")

Base.metadata.create_all(bind = engine)


SECRET_KEY = '12345'

ALGORITHM = 'HS256'

ACCESS_TOKEN = 60

pwd_context = CryptContext(schemes=['bcrypt'], deprecated = 'auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl = 'login')



# сделать вход и регистрацию

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(password: str, hash_password: str):
    return pwd_context.verify(password, hash_password)


def create_access_token(user: User):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN)
    data = {'sub': user.username, 'user_id': user.id, 'role': user.role, 'type': 'access', 'exp': expire}
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user: User):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN)
    data = {'sub': user.username, 'user_id': user.id, 'role': user.role, 'type': 'refresh', 'exp': expire}
    token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
        '''raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен"
        )'''



def create_user(username: str, email: str, password: str, role: str, db: Session):
    new_user = db.scalars(select(User).where((User.username == username) | (User.email == email))).first()
    if new_user is not None:
        return None
    user = User(username = username, password = hash_password(password), email = email, role = role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def login_user(username: str, password: str, db: Session):
    user = db.scalars(select(User).where(User.username == username)).first()
    if user is None:
        return None
    #db.add(user)
    #db.commit()
    #db.refresh(user)
    return user


def get_user(request: Request, db: Session):
    token = request.cookies.get('access_token')
    if not token:
        return None
    payload = decode_token(token)
    if payload is None:
        return None
    if payload.get("type") != 'access':
        return None
    #username = payload.get('sub')
    user_id = payload.get('user_id')
    if user_id is None:
        return None
    user = db.get(User, user_id)
    return user



@app.get('/register')
def register(request: Request):
    return templates.TemplateResponse(request = request, name = 'register.html')

@app.post('/register')
def register_post(request: Request, username: str = Form(...),
                  email: str = Form(...), password: str = Form(...),
                  role: str = Form(...), admin_password: str = Form(...), db: Session = Depends(get_db)):
    if admin_password != 'admin_password' and role == 'admin':
        return templates.TemplateResponse(request = request, name = 'register.html',
                                          context = {'message': 'Неверный пароль для администратора'})
    new_user = create_user(username, email, password, role, db)
    if new_user is None:
        return templates.TemplateResponse(request=request, name='register.html',
                                          context={'message': 'Пользователь с таким username или email уже существует'})
    return templates.TemplateResponse(request=request, name='login.html')


@app.get('/login')
def login(request: Request):
    return templates.TemplateResponse(request = request, name = 'login.html')



@app.post('/login')
def login_post(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = login_user(username, password, db)
    if user is None:
        return templates.TemplateResponse(request=request, name='login.html',
                                          context={'message': 'Пользователя с таким username или email не существует'})
    access_token = create_access_token(user)
    refresh_token, date = create_refresh_token(user)
    token_db = Refresh_token(token = refresh_token, updated_at = date, user_id = user.id)
    db.add(token_db)
    db.commit()
    db.refresh(token_db)
    response = RedirectResponse(url = '/', status_code = 303)
    response.set_cookie(key = 'access_token', value = access_token, httponly = True)
    response.set_cookie(key = 'refresh_token', value = refresh_token, httponly = True)
    return response

@app.get('/logout')
def logout():
    response = RedirectResponse('/login', status_code = 303)
    response.delete_cookie('access_token')
    return response


@app.get('/')
def index(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if user is None:
        return templates.TemplateResponse(request = request, name = 'login.html')
    t = get_user_transaction(user.id, db)
    stat = calculate_statistic(t)
    return templates.TemplateResponse(request = request, name = 'index.html', context = {'t': t, 'stat': stat, 'user': user})

@app.get('/category')
def category(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if user is None:
        return templates.TemplateResponse(request=request, name='login.html')
    category = get_categories(db)
    return templates.TemplateResponse(request = request, name = 'category.html',
                                      context = {'category': category})

@app.post('/category')
def add_category(request: Request, title: str = Form(...), type: str = Form(...), db: Session = Depends(get_db)):
    user = get_user(request, db)
    if user is None:
        return templates.TemplateResponse(request=request, name='login.html')
    if type not in ['income', 'expense']:
        raise HTTPException(status_code = 400, detail = 'Неверная категория')
    create_category(title = title, type = type, user_id = user.id, db = db)
    return RedirectResponse(url = '/category', status_code = 303)



@app.post('/category/delete/{category_id}')
def delete(category_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if user is None:
        return templates.TemplateResponse(request=request, name='login.html')
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(404, 'Категория не найдена')
    if user.id != category.user_id:
        raise HTTPException(403, 'Нет доступа')
    if category.category_transactions:
        return RedirectResponse(url = '/category?error=category_in_use', status_code = 303)
    db.delete(category)
    db.commit()
    return RedirectResponse('/category', status_code = 303)

@app.post('/transaction/add')
def add_transaction(request: Request, title: str = Form(...), cost: int = Form(...), category_id: int = Form(...), db: Session = Depends(get_db)):
    user = get_user(request, db)
    if user is None:
        return templates.TemplateResponse(request=request, name='login.html')
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code = 404, detail = 'Категория не найдена')
    create_transaction(title = title, cost = cost, category_id = category_id, user_id = user.id, db = db)
    return RedirectResponse(url = '/', status_code = 303)

@app.get('/transaction/add')
def add_transaction_page(request: Request, search: str = '', type: str = '',
                         date_from: str = '', date_to: str = '', min_amount: str = '',
                         max_amount: str = '', db: Session = Depends(get_db)):
    user = get_user(request, db)
    if user is None:
        return templates.TemplateResponse(request=request, name='login.html')
    category = get_categories(db)
    print(category)
    transactions = get_user_transaction_1(user.id, db)
    print(transactions)
    if search:
        transactions = transactions.where(Transaction.title.contains(search))
    if type:
        transactions = transactions.where(Transaction.type == type)
    if date_from != '':
        print(date_from)
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        transactions = transactions.where(Transaction.date >= date_from)
    if date_to != '':
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        transactions = transactions.where(Transaction.date <= date_to)
    if min_amount != '':
        transactions = transactions.where(Transaction.cost >= int(min_amount))
    if max_amount != '':
        transactions = transactions.where(Transaction.cost <= int(max_amount))
    #доделать такие же проверки на все данные, отдавать обратно
    transactions = list(db.scalars(transactions).all())
    return templates.TemplateResponse(request = request, name = 'add.html',
                                      context = {'category': category, 'transactions': transactions,
                                                 'search': search, 'type': type, 'date_form': date_from,
                                                 'date_to': date_to, 'min_amount': min_amount,
                                                 'max_amount': max_amount})



@app.post('/transaction/delete/{transaction_id}')
def delete_t(request: Request, transaction_id: int, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if user is None:
        return templates.TemplateResponse(request=request, name='login.html')
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(404, 'Операция не найдена')
    if user.id != transaction.user_id:
        raise HTTPException(403, 'Нет доступа')
    db.delete(transaction)
    db.commit()
    return RedirectResponse('/transaction/add', status_code = 303)



@app.get('/analitic')
def analitic_page(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if user is None:
        return templates.TemplateResponse(request=request, name='login.html')
    return templates.TemplateResponse(request = request, name = 'analitic.html', context = {'user': user})



def figure_to_response(figure):
    buffer = io.BytesIO()
    figure.savefig(buffer, format = 'png')
    buffer.seek(0)
    return StreamingResponse(buffer, media_type = 'image/png')


@app.get('/analitic/balance.png')
def balance_chart(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if user is None:
        return templates.TemplateResponse(request=request, name='login.html')
    t = get_user_transaction(user.id, db)
    t = sorted(t, key = lambda x: x.date)
    balance = 0
    b = []
    l = []
    for i in t:
        if i.category.type == 'income':
            balance += i.cost
        else:
            balance -= i.cost
        b.append(balance)
        l.append(i.date.strftime('%d.%m %H:%M'))
    figure = Figure()
    plt = figure.subplots()
    if l:
        plt.plot(l, b)
        plt.tick_params(labelrotation = 35)
    else:
        plt.text(0.5, 0.5, 'Нет операций', ha = 'center', va = 'center')
    plt.set_title('Изменение баланса')
    plt.set_xlabel('Операция')
    plt.set_ylabel('Баланс')
    plt.grid()
    return figure_to_response(figure)

@app.get('/analitic/bar.png')
def bar_chart(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if user is None:
        return templates.TemplateResponse(request=request, name='login.html')
    c = get_categories(db)
    x = sorted(list(set([i.title for i in c])))
    y1 = {}
    y2 = {}

    for i in range(len(c)):
        print(c[i].type, c[i].title, c[i].category_transactions)
        if c[i].title not in y1:
            y1[c[i].title] = 0
            y2[c[i].title] = 0
        t = 0
        for j in c[i].category_transactions:
            if j.user_id == user.id:
                t += j.cost
        if c[i].type == 'income':
            y1[c[i].title] += t
        else:
            y2[c[i].title] += t
    y11, y22 = [], []
    for i in y1:
        y11.append(y1[i])
        y22.append(y2[i])

    figure = Figure()
    plt = figure.subplots()
    x1 = []
    x2 = []
    for i in range(len(y1)):
        x1.append(i - 0.175)
        x2.append(i + 0.175)
    print(x, y1, y2)
    print(y11, y22)
    if x:
        plt.bar(x1, y11, 0.35, label = 'доходы')
        plt.bar(x2, y22, 0.35, label = 'расходы')
        plt.set_xticks([i for i in range(len(x))])
        plt.set_xticklabels(x)
        plt.tick_params(axis = 'x', labelrotation = 35)
        plt.legend()
    else:
        plt.text(0.5, 0.5, 'Нет операций', ha = 'center', va = 'center')
    plt.set_title('Доходы и расходы по категориям')
    plt.set_xlabel('Категория')
    plt.set_ylabel('Доходы и расходы')
    plt.grid()
    return figure_to_response(figure)


@app.get('/analitic/pie.png')
def pie_chart(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if user is None:
        return templates.TemplateResponse(request=request, name='login.html')
    t = get_user_transaction(user.id, db)
    a = calculate_statistic(t)
    figure = Figure()
    plt = figure.subplots()
    plt.pie(
        [a['income'], a['expense']],
        wedgeprops={'width': 0.3},
        autopct='%1.0f%%',
        pctdistance=0.5
    )
    plt.legend(['Доходы', 'Расходы'], loc='center left', bbox_to_anchor=(1, 0.5))
    return figure_to_response(figure)


@app.post('/upload')
async def upload(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = get_user(request, db)
    if user is None:
        return templates.TemplateResponse(request=request, name='login.html')
    if not file.filename.endswith('.csv') and not file.filename.endswith('.txt'):
        raise HTTPException(400, 'Неподходящий формат файла')
    data = await file.read()
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        text = data.decode('cp1251')
    lines = text.splitlines()
    for i in lines:
        i = i.split(',')
        if len(i) != 5:
            continue
        date = datetime.strptime(i[0],'%d.%m.%Y %H:%M')
        title = i[4]
        cost = int(i[3])
        category_title = i[1]
        type = i[2]
        category = db.scalars(select(Category).where(Category.title == category_title, Category.user_id == user.id)).first()
        if category is None:
            category = Category(title = category_title, type = type, user_id = user.id)
            db.add(category)
            db.flush()
        t = Transaction(title = title, cost = cost, date = date, category_id = category.id, user_id = user.id)
        db.add(t)
    db.commit()
    return RedirectResponse('/transaction/add', status_code = 303)


#сделать выгрузку всей базы в файл excel

@app.get('/download')
async def download(request: Request, db: Session = Depends(get_db)):
    user = get_user(request, db)
    if user is None:
        return templates.TemplateResponse(request=request, name='login.html')
    categories = db.scalars(select(Category).where(Category.user_id == user.id)).all()
    transactions = db.scalars(select(Transaction).where(Transaction.user_id == user.id)).all()
    lines = []
    for i in transactions:
        line = ''
        date = datetime.strptime(str(i.date)[:19], '%Y-%m-%d %H:%M:%S')
        title = i.title
        cost = i.cost
        category_title = i.category.title
        type = i.category.type
        l = [str(date.strftime('%d.%m.%Y %H:%M')), str(category_title), str(type), str(cost), str(title)]
        line = ','.join(l)
        lines.append(line)
    print('lines:', lines)
    file_path = 'test_output.txt'
    with open(file_path, mode = 'w', encoding = 'utf-8') as f:
        for i in lines:
            f.write(i + '\n')

    return FileResponse(path = file_path, filename = 'transactions.txt', media_type = 'text/txt')


#111111111111111111111111111111111111111111111111111111111111111111111111111