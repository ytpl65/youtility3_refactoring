#!/bin/bash

sudo systemctl restart nginx.service
sudo systemctl restart gunicorn.service
sudo supervisorctl restart all
