import os
import logging

import psycopg2
import psycopg2.extensions
from pymongo import MongoClient
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, Float, MetaData, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Задание по Psycopg2
# --------------------------------------------------------------

logger.info("Создаём подключёние к Postgres")
params = {
    "host": os.environ['APP_POSTGRES_HOST'],
    "port": os.environ['APP_POSTGRES_PORT'],
    "user": 'postgres'
}
conn = psycopg2.connect(**params)

# дополнительные настройки
psycopg2.extensions.register_type(
    psycopg2.extensions.UNICODE,
    conn
)
conn.set_isolation_level(
    psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
)
cursor = conn.cursor()

# ВАШ КОД ЗДЕСЬ
# -------------
# таблица movies_top
# movieId (id фильма), ratings_num(число рейтингов), ratings_avg (средний рейтинг фильма)

user_item_query_config = {'MIN_AVG_RATING': 3}

sql_str = (
        """
           SELECT 
              movieid, count(ratings.rating) as rating_num, avg(ratings.rating) as rating_avg 
           INTO movies_top FROM ratings 
           GROUP BY movieid 
           HAVING (avg(ratings.rating) > %(MIN_AVG_RATING)d)
        """ % user_item_query_config
)

# -------------

cursor.execute(sql_str)
conn.commit()

# Проверка - выгружаем данные
cursor.execute("SELECT * FROM movies_top LIMIT 10")
logger.info(
    "Выгружаем данные из таблицы movies_top: (movieid, ratings_num, ratings_avg)\n{}".format(
        [i for i in cursor.fetchall()])
)

"""2018-12-25 14:01:45,241 : INFO : Выгружаем данные из таблицы movies_top: (movieId, ratings_num, ratings_avg)
[(790, 6, 3.16666666666667), (146688, 2, 3.25), (69906, 1, 5.0), (26745, 5, 3.3), (3936, 18, 3.44444444444444),
(88837, 3, 3.16666666666667), (31297, 1, 4.5), (5468, 6, 3.75), (49200, 3, 3.33333333333333), (155078, 1, 4.5)]"""

# Задание по SQLAlchemy
# --------------------------------------------------------------
Base = declarative_base()


class MoviesTop(Base):
    __tablename__ = 'movies_top'
    __table_args__ = {'extend_existing': True}
    movieid = Column(Integer, primary_key=True)
    rating_num = Column(Float)
    rating_avg = Column(Float)
    def __repr__(self):
        return "<User(movieid='%s', rating_num='%s', rating_avg='%s')>" % (self.movieid, self.rating_num, self.rating_avg)


# Создаём сессию

engine = create_engine('postgresql://postgres:@{}:{}'.format(os.environ['APP_POSTGRES_HOST'], os.environ['APP_POSTGRES_PORT']))
Session = sessionmaker(bind=engine)
session = Session()


# --------------------------------------------------------------
# Ваш код здесь
# выберите контент у которого больше 15 оценок (используйте filter)
# и средний рейтинг больше 3.5 (filter ещё раз)
# отсортированный по среднему рейтингу (используйте order_by())
# id такого контента нужно сохранить в массив top_rated_content_ids

top_rated_query = session.query(MoviesTop).filter(MoviesTop.rating_num>15).filter(MoviesTop.rating_avg>3.5).order_by(MoviesTop.rating_avg.desc())

logger.info("Выборка из top_rated_query\n{}".format([i for i in top_rated_query.limit(4)]))

"""logger.info("Выборка из top_rated_query\n{}".format([i for i in top_rated_query.limit(4)]))
2018-12-25 15:54:52,673 : INFO : Выборка из top_rated_query
[<User(movieid='159817', rating_num='23.0', rating_avg='4.47826086956522')>, <User(movieid='2937', rating_num='32.0',
rating_avg='4.46875')>, <User(movieid='38304', rating_num='19.0', rating_avg='4.44736842105263')>,
<User(movieid='2330', rating_num='31.0', rating_avg='4.43548387096774')>]"""

top_rated_content_ids = [
    i[0] for i in top_rated_query.values(MoviesTop.movieid)
][:5]
# --------------------------------------------------------------

# Задание по PyMongo
mongo = MongoClient(**{
    'host': os.environ['APP_MONGO_HOST'],
    'port': int(os.environ['APP_MONGO_PORT'])
})

# Получите доступ к коллекции tags
db = mongo["movie"]
tags_collection = db['tags']

# id контента используйте для фильтрации - передайте его в модификатор $in внутри find
# в выборку должны попать теги фильмов из массива top_rated_content_ids
import pprint as pprint

top_rated_content_ids_str = []
for id in top_rated_content_ids:
    top_rated_content_ids_str.append(str(id))

# id - это идентификатор тега, movieId - идентификатор фильмов. 
# поэтому ищем такие теги, которые сопоставляются нашим фильмам по их movieId.
# в списке top_rated_content_ids_str лежат идентификаторы фильмов.
# по некоторым фильмам совсем нет тегов в нашей коллекции (возможно у меня неполный датасет)
# поэтому в mongo_docs попали два фильма с movieId =  ['2330', '318]
"""»> top_rated_content_ids_str
['159817', '2937', '38304', '2330', '318']
»> print([i for i in db.tags.find({'movieId':'159817'}).limit(3)])
[]
»> print([i for i in db.tags.find({'movieId':'2937'}).limit(3)])
[]
»> print([i for i in db.tags.find({'movieId':'38304'}).limit(3)])
[]"""


mongo_query = tags_collection.find(
        {'movieId': {'$in': top_rated_content_ids_str}}
)
mongo_docs = [
    i for i in mongo_query
]

pprint.pprint("Достали документы из Mongo: {}".format(mongo_docs[:5]))

""">>> pprint.pprint("Достали документы из Mongo: {}".format(mongo_docs[:5]))
("Достали документы из Mongo: [{'_id': ObjectId('5c225c179301aa010ecab560'), "
 "'id': 612, 'name': 'hotel', 'movieId': '318'}, {'_id': "
 "ObjectId('5c225c179301aa010ecab561'), 'id': 2246, 'name': 'confidence', "
 "'movieId': '318'}, {'_id': ObjectId('5c225c179301aa010ecab562'), 'id': 2375, "
 "'name': 'junkie', 'movieId': '318'}, {'_id': "
 "ObjectId('5c225c179301aa010ecab563'), 'id': 3096, 'name': 'book', 'movieId': "
 "'318'}, {'_id': ObjectId('5c225c179301aa010ecab564'), 'id': 6054, 'name': "
 "'friendship', 'movieId': '318'}]")"""

list_popular_tags = []
for doc in mongo_docs:
    list_popular_tags.append(doc['name'])

pprint.pprint('Tеги популярных фильмов: {}'.format(list_popular_tags))

""">>> pprint.pprint('Tеги популярных фильмов: {}'.format(list_popular_tags))
("Tеги популярных фильмов: ['hotel', 'confidence', 'junkie', 'book', "
 "'friendship', 'insanity', 'los angeles', 'drug', 'fbi agent', 'taxi', "
 "'marseille', 'taxi driver', 'pizza delivery', 'pizza boy', 'police officer', "
 "'bank robbery']")"""

id_tags = [(i['id'], i['name']) for i in mongo_docs]


# Задание по Pandas
# --------------------------------------------------------------
# Постройте таблицу их тегов и определите top-5 самых популярных

# формируем DataFrame
tags_df = pd.DataFrame(id_tags, columns=['id', 'tags'])
"""
>>> tags_df
       id            tags
0     612           hotel
1    2246      confidence
2    2375          junkie
3    3096            book
4    6054      friendship
5    6255        insanity
6   12670     los angeles
7   14964            drug
8   18525       fbi agent
9     444            taxi
10    916       marseille
11   1749     taxi driver
12   3330  pizza delivery
13   5983       pizza boy
14  15090  police officer
15  15363    bank robbery
>>> tags_df.groupby('tags').count()
                id
tags              
bank robbery     1
book             1
confidence       1
drug             1
fbi agent        1
friendship       1
hotel            1
insanity         1
junkie           1
los angeles      1
marseille        1
pizza boy        1
pizza delivery   1
police officer   1
taxi             1
taxi driver      1
>>> 
"""
# как видно в нашем случае все теги встречаются только один раз.
# поэтому найдем топ-5 тегов среди всех фильмов в коллекции. 
# для этого создадим датафрейм со всеми тегами и id-ами фильмов


list_all_tags = [i for i in db.tags.find()]
ids_all_tags = [(i['name'], i['movieId']) for i in list_all_tags]
all_tags_df = pd.DataFrame(ids_all_tags, columns=['tags', 'movieId'])

#соединим их слева по именам наших тегов

merged = tags_df.merge(all_tags_df, how = 'left', on='tags')
merged = merged[['tags','id']].groupby(by='tags').count().reset_index()
merged.columns = ['tags', 'count']
top_5_tags = merged.sort_values(by='count', ascending = False).head(5)

print(top_5_tags)
""">>> print(top_5_tags)
              tags  count
5       friendship    411
3             drug    360
9      los angeles    222
6            hotel    154
13  police officer     81
"""

logger.info("Домашка выполнена!")
# --------------------------------------------------------------
