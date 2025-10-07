
# Setup
Github Repo laden lokal.
pip install -r requirements.txt
Lokal braucht ihr dann eine .env Datei im root verzeichnis
Diese ist aus Sicherheitsgründen im .gitignore und beinhaltet aktuell nur 2 Variablen:
    APP_DATABASE_URL=postgresql+psycopg://... 
    APP_ECHO_SQL=...
Legt die Datei an und den Wert der Variablen bekommt ihr von mir.
Wir verwenden eine Postgresdatenbank auf Neon (Ist gratis aber begrenzt auf 100 Rechenstunden und 0,5 GB Speicher-> Sollte kein Problem sein für uns)

# Start the Backend:
uvicorn main:app --reload

# Datenbank migration mit Alembic - Achtung vorsichtig sein ... Man könnte viel kaputt machen
alembic revision --autogenerate -m "beschreibung"
alembic upgrade head (Nach Kontrolle der erstellten Version)

#Anmerkung
Ich war mir nicht so richtig sciher was die ganze App eigenltich sein soll/will. Ich habe das Design daher aktuell so angelgt, dass es eine Liste an Musikelementen gibt. 
Diese können Songs, Alben ... sein und jeder user hat genau eine Collection welcher er Songs daraus zuteilen kann. 
Die Songs kommen aus dem großen allgemeinen Pool den aber nur ADMIN bearbeiten können.

Es stellen sich schon noch einige Fragen. Sollen echte Songs gespeichert werden können und angehört werden können oder soll es nur so wirken?

Soll ein Album dann aus mehreren Songs bestehen? Aktuell ist das noch nicht so ... Weil warum auch?

