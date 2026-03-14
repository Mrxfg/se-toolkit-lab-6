# Task 3 Plan

## Goal
Extend the agent with a new tool that can query the backend API.

## Tool

query_api(method, path, body)

This tool will send HTTP requests to the deployed backend.

## Authentication

Use LMS_API_KEY from environment variables.

## Environment variables

LLM_API_KEY
LLM_API_BASE
LLM_MODEL
LMS_API_KEY
AGENT_API_BASE_URL

## Strategy

Use:
- wiki tools for documentation questions
- query_api for system data questions