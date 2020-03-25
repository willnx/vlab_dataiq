clean:
	-rm -rf build
	-rm -rf dist
	-rm -rf *.egg-info
	-rm -f tests/.coverage
	-docker rm `docker ps -a -q`
	-docker rmi `docker images -q --filter "dangling=true"`

build: clean
	python setup.py bdist_wheel --universal

uninstall:
	-pip uninstall -y vlab-dataiq-api

install: uninstall build
	pip install -U dist/*.whl

test: uninstall install
	cd tests && nosetests -v --with-coverage --cover-package=vlab_dataiq_api

images: build
	docker build -f ApiDockerfile -t willnx/vlab-dataiq-api .
	docker build -f WorkerDockerfile -t willnx/vlab-dataiq-worker .

up:
	docker-compose -p vlabdataiq up --abort-on-container-exit
