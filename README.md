# Teach Me

Оқуға арналған Django жобасы: мәтінді конспектіге айналдырып, одан
флеш-карточкалар жасайды, әр карточканың жауабын, дәйексөзін және тексеру
күйін көрсетеді.

Жоба толығымен localhost-та, аккаунтсыз жұмыс істейді. Бұл — оқу/демо
жоба, өндірістік емес.

## Іске қосу

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver