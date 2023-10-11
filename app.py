import csv, re, os, argparse
import openai
import os
from dotenv import load_dotenv
from duckduckgo_search import DDGS

load_dotenv()
tScores = []
apiCost = 0
openai.api_key = os.environ["OPENAI_API_KEY"]
sysPrompt = (
    "You are a financial advisor. When the user gives you a headline, "
    "respond with a number between -1.0 and 1.0, signifying whether the "
    "headline is extremely negative (-1.0), neutral (0.0), or extremely "
    "positive (1.0) for the stock value of {}."
)

parser = argparse.ArgumentParser()
parser.add_argument(
    "-T",
    "--temp",
    default=0.3,
    help="temperature (variability) of the model. a value between 0.0 and 1.0 (default: 0.3)",
)
parser.add_argument(
    "-t", "--turbo", action="store_true", help="use gpt-3.5-turbo instead of gpt-4"
)

args = parser.parse_args()
modelV = "gpt-4" if args.turbo else "gpt-3.5-turbo"


def rate_headlines(r):
    headline_scores = []
    for i in r:
        headline = i["content"]["title"]
        resp = askGPT(headline)
        try:
            scoreString = re.findall(r"-?\d+\.\d+", resp)[0]
            score = float(scoreString)
        except:
            print("Failed to parse score for " + headline)
        # print("score = ", score)
        headline_scores.append({"headline": headline, "score": score})
    return headline_scores


def askGPT(prompt):
    global apiCost
    resp = openai.ChatCompletion.create(
        model=modelV,
        messages=[
            {"role": "system", "content": sysPrompt},
            {"role": "user", "content": prompt},
        ],
        temperature=args.temp,
    )
    costFactor = [0.03, 0.06] if modelV == "gpt-4" else [0.002, 0.002]
    apiCost += (
        resp["usage"]["prompt_tokens"] / 1000 * costFactor[0]
        + resp["usage"]["completion_tokens"] / 1000 * costFactor[1]
    )
    return resp["choices"][0]["message"]["content"]


def create_report(headline_scores, company):
    with open("Individual_Reports/" + company + ".csv", "w") as f:
        csvwriter = csv.writer(f)
        csvwriter.writerow(["Headline", "Score"])
        for x in headline_scores:
            csvwriter.writerow([x["headline"], x["score"]])
    print("[*] Saved Individual_Reports/" + company + ".csv")


for company in open("companies.txt", "r").readlines():
    company = company.strip()
    scores = []
    headline_scores = []
    sysPrompt = sysPrompt.format(company)
    total = 0  # these two vars for calculating the mean score
    num = 0

    with DDGS() as ddgs:
        r = [
            {"index": i, "content": r, "score": None}
            for i, r in enumerate(
                ddgs.news(
                    company,
                    region="wt-wt",
                    safesearch="off",
                    timelimit="m",
                    max_results=10,
                )
            )
        ]
        headline_scores = rate_headlines(r)
        # print(headline_scores)

        if len(headline_scores) > 0:
            # Create individual company report
            create_report(headline_scores, company)

        else:
            print("[*] No headlines found for " + company)

        # Make Cumulative Report
        totalScore = sum([float(x["score"]) for x in headline_scores])
        mean = totalScore / len(headline_scores)
        tScores.append([company, mean])
        tScores.append(["Total Cost", apiCost])
        with open("report.csv", "w") as f:
            csvwriter = csv.writer(f)
            csvwriter.writerow(["Company", "Mean Score"])
            csvwriter.writerows(tScores)
        print("[*] Saved report.csv")
