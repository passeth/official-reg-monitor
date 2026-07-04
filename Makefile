.PHONY: test fetch status normalize doctor install-dev

install-dev:
	python3 -m pip install -e .

test:
	PYTHONPATH=src python3 -m unittest discover -s tests

fetch:
	PYTHONPATH=src python3 -m official_reg_monitor.cli fetch --force

status:
	PYTHONPATH=src python3 -m official_reg_monitor.cli status

doctor:
	PYTHONPATH=src python3 -m official_reg_monitor.cli doctor

normalize:
	PYTHONPATH=src python3 -m official_reg_monitor.cli normalize
