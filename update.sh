#!/bin/env bash

git pull && sudo docker restart tg_to_vk_bot && sudo docker logs -f tg_to_vk_bot