Для запуска docker-api, скопируй файли на ВМ с установленным докером <br>
`git clone https://github.com/shweper/docker-api.git` <br>
Создай образ: <br>
`sudo docker build -t api-docker ./docker-api/` <br>
Запусти контейнер: <br>
`sudo docker run -v /var/run/docker.sock:/var/run/docker.sock -p 8000:8000 api-docker` <br>
Переходи в свагер чере браузер, провер что работает: <br>
[http://<your_ip>:8000/docs](http://localhost:8000/docs) <br>
